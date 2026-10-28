"""Prueba de punta a punta en esta PC, sin HackRF: emulador + los dos .grc simulados + reconstruir_archivo.py.

    python hackrf_simulada/prueba_completa.py          # ~1 minuto, todo en tiempo real y sin ventanas

Es el mismo procedimiento del laboratorio, automatizado. En cada caso:
  1. arranca el emulador (otro proceso, como el que se deja corriendo en el radioconda Prompt),
  2. arranca el RX simulado, espera 1 s (el AGC se acomoda al ruido) y arranca el TX simulado con un archivo,
  3. cuando el TX termina, para los dos y reconstruye el archivo con reconstruir_archivo.py (huella SHA-256).
Antes verifica que los .grc simulados estén al día con los de grc_hackrf/ y los compila con grcc.
Los archivos de cada caso quedan en build/hackrf_simulada/ (no se tocan grc_hackrf/ ni resultados/).
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BUILD = os.path.join(RAIZ, "build", "hackrf_simulada")
sys.path.insert(0, AQUI)
sys.path.insert(0, RAIZ)
import generar_grc_simulados as gen  # noqa: E402

FS = 2e6
DESVIO_ESPERADO = (9.0 - (-5.0)) * 1e-6 * 914.6e6     # cristales por defecto del emulador (+9 y -5 ppm)

# Cada caso: opciones del emulador, archivo, pasadas y cambios en las interfaces (como mover un control)
CASOS = [
    dict(nombre="archivo de ejemplo, valores por defecto", emulador=[], archivo="ejemplo", repeticiones=3),
    dict(nombre="archivo binario de 40 kB, 2 pasadas (tiempo real sostenido)", emulador=[], archivo=40000,
         repeticiones=2, medir_en=0.6),
    dict(nombre="más ganancia en el RX (VGA 36 dB): mejor S/R", emulador=[], archivo=40000, repeticiones=1,
         rx={"vga_rx": 36}, medir_en=0.6),
    dict(nombre="enlace débil (antenas más lejos, 53 dB): se pierden paquetes y se recuperan en otras pasadas",
         emulador=["--atenuacion", "53"], archivo=6000, repeticiones=5, medir_en=0.5),
    dict(nombre="RX en otra frecuencia (917 MHz): no llega nada", emulador=[], archivo="ejemplo", repeticiones=2,
         rx={"freq_mhz": 917}),
    dict(nombre="demasiada ganancia en el RX (LNA 40, VGA 50, amplificador): el ADC satura", emulador=[],
         archivo="ejemplo", repeticiones=2, rx={"lna": 40, "vga_rx": 50, "amp_rx": True}),
    dict(nombre="amplitud digital 0,7 en el TX: los picos pasan de ±1 y el DAC recorta", emulador=[],
         archivo="ejemplo", repeticiones=2, tx={"amplitud": 0.7}),
    dict(nombre="RX sintonizado 25 kHz arriba (915,025 MHz): el FLL corrige el desvío total", emulador=[],
         archivo=6000, repeticiones=2, rx={"freq_mhz": 915.025}, medir_en=0.5),
    dict(nombre="cable SIN atenuador, TX al máximo (VGA 47 + amplificador): aviso de daño", emulador=[
        "--atenuacion", "0"], archivo="ejemplo", repeticiones=1, tx={"vga_tx": 47, "amp_tx": True}),
]


# --------------------------------------------------------------------------- en el proceso de cada caso
def correr_caso(caso, carpeta):
    """Corre RX y TX simulados (en este proceso, sin ventanas) y devuelve lo que mostrarían las interfaces."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, BUILD)
    from PyQt5 import Qt
    import hackrf_rx_archivo_sim
    import hackrf_tx_archivo_sim
    import reconstruir_archivo as rec

    app = Qt.QApplication.instance() or Qt.QApplication([])

    def esperar(segundos):
        fin = time.time() + segundos
        while time.time() < fin:
            app.processEvents()
            time.sleep(0.02)

    if caso["archivo"] == "ejemplo":
        archivo = os.path.join(RAIZ, "grc_hackrf", "archivo_a_enviar.txt")
    else:
        import numpy as np
        archivo = os.path.join(carpeta, "prueba_%d_bytes.bin" % caso["archivo"])
        with open(archivo, "wb") as f:
            f.write(np.random.default_rng(7).integers(0, 256, caso["archivo"], dtype=np.uint8).tobytes())

    os.chdir(carpeta)                                  # el RX escribe paquetes_recibidos.bin acá
    rx = hackrf_rx_archivo_sim.hackrf_rx_archivo_sim()
    for clave, valor in caso.get("rx", {}).items():
        getattr(rx, "set_" + clave)(valor)
    rx.start()
    rx.flowgraph_started.set()
    esperar(1.0)

    tx = hackrf_tx_archivo_sim.hackrf_tx_archivo_sim(archivo=archivo, repeticiones=caso["repeticiones"])
    for clave, valor in caso.get("tx", {}).items():
        getattr(tx, "set_" + clave)(valor)
    # El contador de pasadas del TX (bloque Head) va ~0,5 s adelantado: entre el Head y la "placa" hay buffers.
    # Por eso se espera por tiempo: lo que dura la transmisión, más hasta que el RX deja de recibir paquetes.
    duracion = caso["repeticiones"] * tx.duracion_pasada
    t0 = time.time()
    tx.start()
    tx.flowgraph_started.set()
    medido = {}
    ultimo, t_ultimo = 0, None
    while time.time() - t0 < duracion + 30:
        esperar(0.05)
        t = time.time() - t0
        if rx.crc.nitems_written(0) != ultimo:
            ultimo, t_ultimo = rx.crc.nitems_written(0), t
        if not medido and t >= 0.3 + caso.get("medir_en", 99) * duracion:
            rx.set_w_fll(rx.fll_sonda.level())         # lo mismo que muestra el indicador "desvío" del RX
            rx.set_w_costas(rx.costas_sonda.level())
            medido = {"desvio_hz": rx.cfo_hz, "es_n0_db": rx.estimador_snr.snr()}
        if t > duracion + 1.0 and (t_ultimo is None or t - t_ultimo > 1.0):
            break
    tx.stop()
    tx.wait()
    rx.stop()
    rx.wait()
    info = rec.reconstruir(os.path.join(carpeta, "paquetes_recibidos.bin"), n=tx.N)
    return dict(medido, identico=info["identico"], recibidos=info["recibidos"], perdidos=info["perdidos"],
                per=info["per"], enviados=caso["repeticiones"] * tx.n_paq, duracion_teorica=duracion,
                ultimo_paquete=t_ultimo)


# --------------------------------------------------------------------------- en el proceso principal
def python():
    return sys.executable


def grc_al_dia():
    viejos = []
    for nombre in gen.NOMBRES:
        ruta, texto = gen.generar(nombre)
        with open(ruta, encoding="utf-8") as f:
            if f.read() != texto:
                viejos.append(os.path.basename(ruta))
    return viejos


def compilar():
    os.makedirs(BUILD, exist_ok=True)
    grcc = shutil.which("grcc") or os.path.join(os.path.dirname(sys.executable), "Scripts", "grcc.exe")
    for nombre in gen.NOMBRES:
        r = subprocess.run([grcc, "-o", BUILD, os.path.join(AQUI, nombre + "_sim.grc")], capture_output=True,
                           text=True)
        if r.returncode != 0:
            sys.exit("grcc falló con %s_sim.grc:\n%s" % (nombre, r.stdout + r.stderr))


class Emulador:
    """emulador_hackrf.py en otro proceso; guarda lo que imprime."""

    def __init__(self, opciones):
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
        self.proceso = subprocess.Popen([python(), "-u", os.path.join(AQUI, "emulador_hackrf.py"), "--semilla", "1",
                                         "--cada", "1"] + opciones, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=entorno)
        self.lineas = []
        threading.Thread(target=self._leer, daemon=True).start()
        fin = time.time() + 15
        while not any("listo" in x for x in self.lineas):
            if self.proceso.poll() is not None or time.time() > fin:
                sys.exit("El emulador no arrancó:\n" + "".join(self.lineas))
            time.sleep(0.05)

    def _leer(self):
        for linea in self.proceso.stdout:
            self.lineas.append(linea)

    def cerrar(self):
        self.proceso.terminate()
        self.proceso.wait()
        return "".join(self.lineas)


def correr_en_otro_proceso(caso, carpeta):
    r = subprocess.run([python(), "-X", "utf8", os.path.abspath(__file__), "--caso", json.dumps(caso), carpeta],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    resultado = [x for x in r.stdout.splitlines() if x.startswith("RESULTADO ")]
    if not resultado:
        raise RuntimeError("el caso no terminó:\n" + r.stdout[-3000:] + r.stderr[-3000:])
    return json.loads(resultado[-1][len("RESULTADO "):])


def per_teorico(es_n0_db, n=200):
    import math
    p = 0.5 * math.erfc(math.sqrt(10 ** (es_n0_db / 10) / 2))
    return 1 - (1 - p) ** (8 * (n + 18))


def verificar(i, caso, r, salida_emulador):
    """Devuelve la lista de problemas del caso i (vacía si está todo bien)."""
    problemas = []
    if "se atrasó" in salida_emulador:
        problemas.append("el emulador no pudo ir en tiempo real")
    if i in (0, 1, 2, 3) and not r["identico"]:
        problemas.append("el archivo reconstruido no es idéntico")
    if i in (0, 1, 2) and r["perdidos"] > 0:
        problemas.append("se perdieron paquetes con buena señal")
    if i in (1, 2, 3):
        if abs(r["desvio_hz"] - DESVIO_ESPERADO) > 0.05 * DESVIO_ESPERADO:
            problemas.append("desvío medido %.0f Hz (el emulador puso %.0f Hz)" % (r["desvio_hz"], DESVIO_ESPERADO))
    if i == 1 and not r["duracion_teorica"] < r["ultimo_paquete"] < r["duracion_teorica"] + 0.6:
        problemas.append("el último paquete llegó a los %.2f s (en tiempo real: a los %.2f s, más el arranque)"
                         % (r["ultimo_paquete"], r["duracion_teorica"]))
    if i == 3 and not 0 < r["per"] < 0.6:
        problemas.append("se esperaban algunos paquetes perdidos (PER %.2f)" % r["per"])
    if i == 4 and (r["recibidos"] > 0 or "NO llega" not in salida_emulador):
        problemas.append("con el RX en otra frecuencia no debería llegar nada")
    if i == 5 and "SATURA" not in salida_emulador:
        problemas.append("el emulador no avisó la saturación")
    if i == 6 and "recorta" not in salida_emulador:
        problemas.append("el emulador no avisó que el DAC del TX recorta")
    if i == 7:
        esperado = DESVIO_ESPERADO - 25e3
        if not r["identico"] or abs(r["desvio_hz"] - esperado) > 1e3:
            problemas.append("desvío medido %.0f Hz (esperado %.0f Hz)" % (r["desvio_hz"], esperado))
    if i == 8 and "CUIDADO" not in salida_emulador:
        problemas.append("el emulador no avisó que la potencia dañaría una HackRF real")
    return problemas


def main(solo=None):
    viejos = grc_al_dia()
    if viejos:
        sys.exit("Los .grc simulados no están al día con grc_hackrf/ (%s).\nCorrer primero:"
                 " python hackrf_simulada/generar_grc_simulados.py" % ", ".join(viejos))
    print("  OK    los .grc simulados están al día con grc_hackrf/")
    compilar()
    print("  OK    compilan con grcc")
    fallas = 0
    for i, caso in enumerate(CASOS):
        if solo and i + 1 not in solo:
            continue
        carpeta = os.path.join(BUILD, "caso_%d" % (i + 1))
        shutil.rmtree(carpeta, ignore_errors=True)
        os.makedirs(carpeta)
        t0 = time.time()
        emulador = Emulador(caso["emulador"])
        try:
            r = correr_en_otro_proceso(caso, carpeta)
        except Exception as error:  # noqa: BLE001
            r, problemas = None, [str(error)]
        salida = emulador.cerrar()
        if r is not None:
            problemas = verificar(i, caso, r, salida)
        fallas += bool(problemas)
        print("  %-5s %d. %s  (%.0f s)" % ("FALLA" if problemas else "OK", i + 1, caso["nombre"], time.time() - t0))
        if r is not None:
            texto = "        paquetes %d de %d (PER %.3f), archivo %s" % (
                r["recibidos"], r["enviados"], r["per"], "IDÉNTICO" if r["identico"] else "distinto")
            if "desvio_hz" in r:
                texto += "; el RX mide desvío %+.1f kHz y Es/N0 %.1f dB (PER teórico %.3f)" % (
                    r["desvio_hz"] / 1e3, r["es_n0_db"], per_teorico(r["es_n0_db"]))
            print(texto)
            senal = [x.strip() for x in salida.splitlines() if "S/R" in x or "SATURA" in x or "NO llega" in x
                     or "recorta" in x]
            if senal:
                print("        emulador:", senal[len(senal) // 2])
        for p in problemas:
            print("        PROBLEMA:", p)
        if problemas:
            print("        --- salida del emulador ---\n" + "".join("        " + x for x in salida.splitlines(True)))
    print("\n%d casos, %d fallas" % (len(solo or CASOS), fallas))
    return 1 if fallas else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--caso":
        resultado = correr_caso(json.loads(sys.argv[2]), sys.argv[3])
        print("RESULTADO " + json.dumps(resultado))
        sys.stdout.flush()
        os._exit(0)                 # no espera a los hilos de 'Function Probe' de las interfaces
    sys.exit(main([int(x) for x in sys.argv[1:]]))        # p. ej. "prueba_completa.py 2 4": solo esos casos
