#!/usr/bin/env python3
"""
Pruebas de grc_hackrf/ SIN HackRF: los bloques 'Soapy HackRF Sink/Source' se reemplazan por un HackRF simulado.

    python tests/test_hackrf.py        # ~1 minuto

Se compilan los .grc reales con grcc. El transmisor entrega sus muestras a un canal de laboratorio simulado:
  - desvío de frecuencia entre los osciladores de los dos HackRF (kHz) y relojes de muestreo distintos (ppm),
  - ruido de fase, atenuación, portadora residual (pico de continua) y ruido blanco,
  - ruido solo antes de que empiece la transmisión (el receptor se enciende primero),
y el receptor procesa esas muestras como si vinieran del HackRF. Después se reconstruye el archivo con
reconstruir_archivo.py y se compara con el original.
"""
import hashlib
import importlib
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")     # los flowgraphs con interfaz corren sin ventana

import numpy as np  # noqa: E402
from gnuradio import analog, blocks, filter as grfilter, gr, soapy  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRC_DIR = os.path.join(ROOT, "grc_hackrf")
sys.path.insert(0, ROOT)
import reconstruir_archivo as rec  # noqa: E402

BUILD = tempfile.mkdtemp(prefix="pruebas_hackrf_")
_KEEP = []          # flowgraphs con interfaz: se mantienen vivos hasta el final (sus 'Function Probe' siguen leyendo)
FS = 2e6            # muestras/s del HackRF (variable samp_rate de los .grc)
_MODULES = {}


def compile_grc(name):
    if name in _MODULES:
        return _MODULES[name]
    grcc = shutil.which("grcc") or os.path.join(os.path.dirname(sys.executable), "Scripts", "grcc.exe")
    r = subprocess.run([grcc, "-o", BUILD, os.path.join(GRC_DIR, name)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    if BUILD not in sys.path:
        sys.path.insert(0, BUILD)
    _MODULES[name] = importlib.import_module(name[:-4])
    return _MODULES[name]


def qt_app():
    from PyQt5 import Qt
    app = Qt.QApplication.instance() or Qt.QApplication([])
    _KEEP.append(app)
    return app


class _ControlesHackRF:
    """Los métodos que llama el código generado por GRC sobre los bloques Soapy (acá no hacen nada)."""
    def set_sample_rate(self, *a): pass
    def set_bandwidth(self, *a): pass
    def set_frequency(self, *a): pass
    def set_gain(self, *a): pass


class HackRFSimuladoTX(gr.hier_block2, _ControlesHackRF):
    def __init__(self, *args, **kw):
        gr.hier_block2.__init__(self, "hackrf_tx_simulado", gr.io_signature(1, 1, gr.sizeof_gr_complex),
                                gr.io_signature(0, 0, 0))
        self.muestras = blocks.vector_sink_c()
        self.connect(self, self.muestras)


class HackRFSimuladoRX(gr.hier_block2, _ControlesHackRF):
    senal = None                                        # muestras que "recibe" (las fija cada prueba)

    def __init__(self, *args, **kw):
        gr.hier_block2.__init__(self, "hackrf_rx_simulado", gr.io_signature(0, 0, 0),
                                gr.io_signature(1, 1, gr.sizeof_gr_complex))
        self.fuente = blocks.vector_source_c(HackRFSimuladoRX.senal.tolist(), False)
        self.connect(self.fuente, self)


soapy.sink = HackRFSimuladoTX           # el código generado llama soapy.sink(...) / soapy.source(...)
soapy.source = HackRFSimuladoRX


def transmitir(archivo, repeticiones):
    """Corre hackrf_tx_archivo con el HackRF simulado y devuelve las muestras que habría transmitido."""
    mod = compile_grc("hackrf_tx_archivo.grc")
    qt_app()
    tb = mod.hackrf_tx_archivo(archivo=archivo, repeticiones=repeticiones)
    tb.start()
    tb.flowgraph_started.set()
    tb.wait()                                          # termina solo: el bloque Head corta después de las pasadas
    _KEEP.append(tb)
    return np.array(tb.hackrf_tx.muestras.data(), dtype=np.complex64), tb


def canal_laboratorio(tx, cfo_hz, ppm, es_n0_db, ganancia=0.03, fase_ruido=0.003, dc=0.01, silencio_s=0.3,
                      semilla=1):
    """Lo que entregaría el HackRF receptor: tx con desvíos, ruido y un tramo previo con ruido solo
    (el receptor se enciende antes que el transmisor; en ese tramo el AGC se ajusta al nivel del ruido)."""
    rng = np.random.default_rng(semilla)
    x = np.concatenate([np.zeros(int(silencio_s * FS), np.complex64), tx])
    x = x * np.exp(1j * np.cumsum(rng.normal(0, fase_ruido, len(x)))).astype(np.complex64)
    tb = gr.top_block()
    src = blocks.vector_source_c(x.tolist(), False)
    reloj = grfilter.mmse_resampler_cc(0.0, 1.0 + ppm * 1e-6)                 # relojes de muestreo distintos
    osc = blocks.rotator_cc(2 * math.pi * cfo_hz / FS)                           # osciladores distintos
    aten = blocks.multiply_const_cc(ganancia * np.exp(0.7j))
    # potencia de la señal antes de atenuar: amplitud 0,5 -> 0,25 por muestra; Es/N0 = P / sigma^2 * sps (8)
    sigma = math.sqrt(0.25 * ganancia ** 2 * 8 / 10 ** (es_n0_db / 10))
    ruido = analog.noise_source_c(analog.GR_GAUSSIAN, sigma, semilla)
    suma = blocks.add_cc()
    portadora = blocks.add_const_cc(dc * (1 + 0.5j))                             # pico de continua del HackRF
    snk = blocks.vector_sink_c()
    tb.connect(src, reloj, osc, aten, (suma, 0))
    tb.connect(ruido, (suma, 1))
    tb.connect(suma, portadora, snk)
    tb.run()
    return np.array(snk.data(), dtype=np.complex64)


def recibir(senal, carpeta):
    """Corre hackrf_rx_archivo con el HackRF simulado; devuelve el flowgraph (los archivos quedan en carpeta)."""
    mod = compile_grc("hackrf_rx_archivo.grc")
    qt_app()
    HackRFSimuladoRX.senal = senal
    cwd = os.getcwd()
    os.chdir(carpeta)                                 # paquetes_recibidos.bin / datos_recibidos.bin van acá
    try:
        tb = mod.hackrf_rx_archivo()
        tb.start()
        tb.flowgraph_started.set()
        tb.wait()                                     # termina cuando se acaban las muestras
        _KEEP.append(tb)
    finally:
        os.chdir(cwd)
    return tb


def archivo_de_prueba(carpeta, nombre, n_bytes, semilla=3):
    rng = np.random.default_rng(semilla)
    texto = ("Prueba de laboratorio con HackRF - Sistemas de Comunicaciones Digitales - FACET UNT\n" * 40).encode()
    datos = texto + rng.integers(0, 256, n_bytes - len(texto), dtype=np.uint8).tobytes()
    ruta = os.path.join(carpeta, nombre)
    with open(ruta, "wb") as f:
        f.write(datos)
    return ruta, datos


def enlace(cfo_hz, ppm, es_n0_db, repeticiones, n_bytes=12345, semilla=1):
    carpeta = tempfile.mkdtemp(prefix="lab_", dir=BUILD)
    ruta, datos = archivo_de_prueba(carpeta, "foto_de_prueba.bin", n_bytes)
    tx, tb_tx = transmitir(ruta, repeticiones)
    rx = canal_laboratorio(tx, cfo_hz, ppm, es_n0_db, semilla=semilla)
    tb_rx = recibir(rx, carpeta)
    info = rec.reconstruir(os.path.join(carpeta, "paquetes_recibidos.bin"), n=200)
    return carpeta, datos, info, tb_tx, tb_rx


def cfo_medido(tb):
    """Lo mismo que muestra el indicador 'Desvío de frecuencia' de la interfaz del receptor."""
    tb.set_w_fll(tb.fll_sonda.level())             # promedios de 0,1 s de las frecuencias de FLL y Costas
    tb.set_w_costas(tb.costas_sonda.level())
    return tb.cfo_hz


def per_teorico(es_n0_db, n=200):
    """PER de 4-QAM diferencial: cada error del canal (prob. p por eje) arruina 2 bits de la misma trama."""
    p = 0.5 * math.erfc(math.sqrt(10 ** (es_n0_db / 10) / 2))
    return 1 - (1 - p) ** (8 * (n + 18))


# --------------------------------------------------------------------- pruebas
def test_los_grc_compilan_con_grcc():
    compile_grc("hackrf_tx_archivo.grc")
    compile_grc("hackrf_rx_archivo.grc")


def test_archivo_llega_identico_con_desvio_de_15_khz():
    carpeta, datos, info, tb_tx, tb_rx = enlace(cfo_hz=15e3, ppm=20, es_n0_db=22, repeticiones=2)
    assert info["identico"] is True, info
    assert open(info["salida"], "rb").read() == datos
    assert info["perdidos"] == 0 and not info["faltan"], info
    assert info["recibidos"] == 2 * tb_tx.n_paq, (info["recibidos"], tb_tx.n_paq)
    # datos_recibidos.bin (sin reconstruir) empieza con el archivo completo de la primera pasada
    directo = open(os.path.join(carpeta, "datos_recibidos.bin"), "rb").read()
    assert directo[:len(datos)] == datos
    assert abs(cfo_medido(tb_rx) / 15e3 - 1) < 0.02, cfo_medido(tb_rx)


def test_peor_desvio_entre_dos_hackrf_40_khz():
    # ±20 ppm cada uno a 915 MHz: hasta ~37 kHz entre los dos osciladores
    carpeta, datos, info, tb_tx, tb_rx = enlace(cfo_hz=40e3, ppm=-20, es_n0_db=22, repeticiones=1, semilla=2)
    assert info["identico"] is True and info["perdidos"] == 0, info
    assert abs(cfo_medido(tb_rx) / 40e3 - 1) < 0.02, cfo_medido(tb_rx)


def test_desvio_negativo_y_ruido_con_perdidas_se_recupera_con_repeticiones():
    # Es/N0 = 12 dB (Eb/N0 = 9 dB): se pierde ~6 % de las tramas (teoría); con 4 pasadas llega todo
    carpeta, datos, info, tb_tx, tb_rx = enlace(cfo_hz=-20e3, ppm=-15, es_n0_db=12, repeticiones=4, semilla=5)
    assert info["identico"] is True, info
    teo = per_teorico(12)
    assert 0.5 * teo < info["per"] < 2 * teo, (info["per"], teo)
    assert abs(cfo_medido(tb_rx) / -20e3 - 1) < 0.02, cfo_medido(tb_rx)


def test_nombre_largo_con_acentos():
    carpeta = tempfile.mkdtemp(prefix="lab_", dir=BUILD)
    nombre = "información_del_laboratorio_de_comunicaciones_ñandú.txt"            # más de 40 bytes en UTF-8
    ruta, datos = archivo_de_prueba(carpeta, nombre, 4000)
    tx, tb_tx = transmitir(ruta, 1)
    recibir(canal_laboratorio(tx, -5e3, 10, 25), carpeta)
    info = rec.reconstruir(os.path.join(carpeta, "paquetes_recibidos.bin"), n=200)
    assert info["identico"] is True, info
    assert nombre.startswith(info["descripcion"]["nombre"]) and len(info["descripcion"]["nombre"]) >= 30, info


def test_archivo_inexistente_manda_un_aviso():
    carpeta = tempfile.mkdtemp(prefix="lab_", dir=BUILD)
    tx, tb_tx = transmitir(os.path.join(carpeta, "no_existe.txt"), 1)
    recibir(canal_laboratorio(tx, 3e3, 5, 25), carpeta)
    info = rec.reconstruir(os.path.join(carpeta, "paquetes_recibidos.bin"), n=200)
    assert info["descripcion"]["nombre"] == "ERROR_archivo_no_encontrado.txt", info
    assert b"No se encontro el archivo" in open(info["salida"], "rb").read()


def _registros(datos, n, pasadas, perdidos):
    """Simula paquetes_recibidos.bin: 'pasadas' veces [paquetes de datos + descripción], sin los 'perdidos'."""
    n_datos = (len(datos) + n - 1) // n
    relleno = datos + bytes(n_datos * n - len(datos))
    desc = ("ARCHIVO|x.bin|%d|%d|%d|%s|" % (len(datos), n, n_datos + 1, hashlib.sha256(datos).hexdigest())).encode()
    cuerpos = [relleno[k * n:(k + 1) * n] for k in range(n_datos)] + [desc.ljust(n, b"\0")]
    orden = list(range(n_datos + 1)) * pasadas
    return b"".join(bytes([k // 256, k % 256]) + cuerpos[k] for i, k in enumerate(orden) if i not in perdidos)


def test_reconstruir_ordena_descarta_repetidos_y_cuenta_perdidos():
    carpeta = tempfile.mkdtemp(prefix="rec_", dir=BUILD)
    datos = np.random.default_rng(9).integers(0, 256, 3000, dtype=np.uint8).tobytes()   # 15 paquetes + 1 final
    ruta = os.path.join(carpeta, "paquetes_recibidos.bin")
    # se pierden los paquetes 3 y 4 de la 1.a pasada y el 7 de la 2.a: cada uno llegó en alguna pasada
    with open(ruta, "wb") as f:
        f.write(_registros(datos, 200, 2, {3, 4, 16 + 7}))
    info = rec.reconstruir(ruta, n=200)
    assert info["identico"] is True and info["faltan"] == [], info
    assert info["perdidos"] == 3 and info["recibidos"] == 29, info
    assert abs(info["per"] - 3 / 32) < 1e-12, info["per"]
    assert os.path.basename(info["salida"]) == "recibido_x.bin"
    assert open(info["salida"], "rb").read() == datos
    # el paquete 5 se pierde en las dos pasadas: el archivo queda incompleto y la huella no coincide
    with open(ruta, "wb") as f:
        f.write(_registros(datos, 200, 2, {5, 16 + 5}))
    info = rec.reconstruir(ruta, n=200)
    assert info["identico"] is False and info["faltan"] == [5], info


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        t0 = time.time()
        try:
            fn()
            print("  OK    %-72s %5.1fs" % (name, time.time() - t0))
        except Exception:  # noqa: BLE001
            failed += 1
            import traceback
            print("  FALLA %-72s" % name)
            traceback.print_exc()
    print("\n%d pruebas, %d fallas" % (len(tests), failed))
    shutil.rmtree(BUILD, ignore_errors=True)
    sys.stdout.flush()
    os._exit(1 if failed else 0)       # os._exit: no espera a los hilos de 'Function Probe' de las interfaces
