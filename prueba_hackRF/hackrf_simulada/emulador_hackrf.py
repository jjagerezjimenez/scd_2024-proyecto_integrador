"""Emulador de DOS HackRF One y del aire entre ellas, para probar grc_hackrf/ sin las placas.

Dejarlo corriendo en un "radioconda Prompt" (se corta con Ctrl+C):

    python hackrf_simulada/emulador_hackrf.py                    # antenas a unos metros
    python hackrf_simulada/emulador_hackrf.py --atenuacion 60    # más lejos
    python hackrf_simulada/emulador_hackrf.py --help             # todas las opciones

y después abrir en GNU Radio Companion hackrf_simulada/hackrf_rx_archivo_sim.grc y hackrf_tx_archivo_sim.grc
(F6, primero el RX). Esos .grc son copias de los de grc_hackrf/ en las que el bloque Soapy HackRF se cambió por
bloques de red estándar de GNU Radio (ver generar_grc_simulados.py):

    TX (.grc) --TCP: muestras--> [ HackRF TX -> aire -> HackRF RX ] --UDP: I/Q de 8 bits--> RX (.grc)
    TX y RX   --UDP: frecuencia y ganancias-->  (este programa)

Qué le hace a cada bloque de muestras (Enlace.procesar, en este orden):
 1. DAC del TX (8 bits): recorta si |I| o |Q| pasan de 1 y suma la fuga del oscilador local (pico en el centro).
 2. Potencia del TX: depende de la ganancia VGA (0-47 dB) y del amplificador (+14 dB).
 3. Relojes: cada placa tiene un cristal con error (--ppm-tx, --ppm-rx). Eso corre la frecuencia de la señal
    (desvío de portadora) y hace que el RX tome las muestras a un ritmo apenas distinto del TX. Además: ruido de
    fase y el corrimiento del cristal del TX mientras se calienta (--deriva).
 4. Aire: atenuación (--atenuacion) y una fase cualquiera. Sintonía: la señal se corre la diferencia entre la
    frecuencia del TX y la del RX; si pasa de la mitad del ancho de banda (1 MHz) no llega nada.
 5. RX: ruido térmico (figura de ruido), ganancias LNA (0-40 dB, de a 8), VGA (0-62 dB, de a 2) y amplificador
    (+11 dB), componente continua (pico en el centro) y ADC de 8 bits (satura si la señal es muy grande).
 6. Tiempo real: entrega 2 millones de muestras por segundo, como la placa, y toma las del TX al mismo ritmo.

Los números (dBm, figura de ruido) son aproximados, del orden de los de una HackRF One a 915 MHz. Lo que importa
es el comportamiento: más ganancia sube la señal y el ruido; demasiada satura el ADC; poca deja la señal en pocos
niveles del ADC de 8 bits; con el TX y el RX en frecuencias distintas no llega nada.
"""
import argparse
import math
import socket
import sys
import time

import numpy as np

# Direcciones (las mismas que generar_grc_simulados.py). Todo queda dentro de la PC (127.0.0.1).
EMULADOR = "127.0.0.1"
PUERTO_TX = 5550                # TCP: muestras del TX
PUERTO_RX = 5551                # UDP: muestras al RX
PUERTO_AJUSTES = 5552           # UDP: frecuencia y ganancias de los dos .grc
MUESTRAS_POR_PAQUETE = 4096     # cada paquete UDP al RX lleva 4096 pares (I, Q) de 8 bits = 8192 bytes
BLOQUE = 4 * MUESTRAS_POR_PAQUETE   # se procesa de a 16384 muestras (8,2 ms a 2 Ms/s)

# HackRF One, valores aproximados a 915 MHz
TX_POTENCIA_MAX_DBM = 10.0      # señal a escala completa (|x| = 1) con VGA 47 dB y amplificador encendido
TX_AMP_DB = 14.0
RX_AMP_DB = 11.0
RX_FIGURA_RUIDO_DB = {False: 14.0, True: 8.0}   # sin / con amplificador
RX_ESCALA_ADC_DBM = -10.0       # potencia (después de las ganancias) que llena el ADC de 8 bits
RX_MAXIMO_DBM = -5.0            # más que esto en la entrada puede dañar una HackRF real
FUGA_LO_TX = 0.02 * np.exp(0.4j)     # portadora residual del TX (relativa a la escala completa del DAC)
CONTINUA_RX = 0.006 + 0.004j         # componente continua del RX (relativa a la escala completa del ADC)
RUIDO_FASE = 0.003              # desvío estándar (rad) del paso de fase por muestra de los dos osciladores
CALENTAMIENTO_S = 180.0         # constante de tiempo del corrimiento del cristal al calentarse
KT_DBM_HZ = -174.0              # ruido térmico a temperatura ambiente

AJUSTES_POR_DEFECTO = {         # hasta que cada .grc mande los suyos (son los valores iniciales de las interfaces)
    "tx": {"frecuencia": None, "muestreo": 2e6, "vga": 20.0, "amp": 0.0},
    "rx": {"frecuencia": None, "muestreo": 2e6, "lna": 16.0, "vga": 20.0, "amp": 0.0},
}


def leer_ajustes(texto):
    """b'equipo=tx frecuencia=914600000.0 vga=20.0 amp=0' -> {'equipo': 'tx', 'frecuencia': 914600000.0, ...}"""
    ajustes = {}
    for par in texto.decode("ascii", "replace").split():
        clave, _, valor = par.partition("=")
        ajustes[clave] = valor if clave == "equipo" else float(valor)
    return ajustes


def ganancias_hackrf(tx, rx):
    """Como el driver de la HackRF: limita los rangos y redondea hacia abajo a los pasos de cada etapa."""
    vga_tx = min(max(int(tx["vga"]), 0), 47)
    lna = min(max(int(rx["lna"]) // 8 * 8, 0), 40)
    vga_rx = min(max(int(rx["vga"]) // 2 * 2, 0), 62)
    return vga_tx, lna, vga_rx


class Reloj:
    """Pasa de las muestras del reloj del TX a las del reloj del RX (cada cristal tiene su error en ppm).

    Con 14 ppm de diferencia, por cada segundo el RX toma 28 muestras menos (o más) de las que mandó el TX: los
    instantes de muestreo se van corriendo de a poco. Se interpola con un filtro sinc de 16 coeficientes y 256
    retardos fraccionarios (fases)."""
    COEF, FASES, MARGEN = 16, 256, 8

    def __init__(self):
        k = np.arange(self.COEF) - (self.COEF // 2 - 1)                       # -7 ... 8
        t = k[None, :] - np.arange(self.FASES)[:, None] / self.FASES
        ventana = np.i0(6 * np.sqrt(np.clip(1 - (t / (self.COEF / 2)) ** 2, 0, 1))) / np.i0(6)
        h = np.sinc(t) * ventana
        self.h = (h / h.sum(axis=1, keepdims=True))[:, ::-1].astype(np.float32)   # invertidos para np.convolve
        self.x = np.zeros(self.COEF + self.MARGEN, np.complex64)                # últimas muestras del TX
        self.t = float(self.COEF // 2 - 1 + self.MARGEN)                        # posición en self.x de la próxima

    def cuantas(self, n, r):
        """Cuántas muestras nuevas del TX hacen falta para n muestras del RX (r = muestras del TX por cada una)."""
        return max(0, int(math.floor(self.t + r * (n - 1))) + self.COEF // 2 + 1 - len(self.x))

    def procesar(self, nuevas, n, r):
        x = np.concatenate([self.x, nuevas])
        y = np.empty(n, np.complex64)
        # posición de cada muestra j del RX respecto de j, en 1/256 de muestra (cambia muy despacio)
        q = np.floor((self.t + (r - 1.0) * np.arange(n)) * self.FASES).astype(np.int64)
        cortes = np.flatnonzero(np.diff(q)) + 1
        for a, b in zip(np.r_[0, cortes], np.r_[cortes, n]):     # tramos con el mismo retardo: un filtro FIR
            d, f = divmod(int(q[a]), self.FASES)
            y[a:b] = np.convolve(x[a + d - (self.COEF // 2 - 1): b + d + self.COEF // 2], self.h[f], "valid")
        p = self.t + r * n
        i = int(math.floor(p)) - (self.COEF // 2 - 1) - self.MARGEN
        self.x, self.t = x[i:], p - i
        return y


class EntradaTX:
    """Muestras que manda el .grc del TX por TCP. Se leen solo las que hacen falta: si el emulador no lee, el TX
    se frena (igual que con la placa, que pide muestras a 2 Ms/s)."""

    def __init__(self):
        self.conexion = None
        self.pendiente = bytearray()

    def nueva(self, conexion):
        self.cerrar()
        conexion.setblocking(False)
        self.conexion = conexion
        print("  >> se conectó el TX", flush=True)

    def cerrar(self, motivo=None):
        if self.conexion is not None:
            self.conexion.close()
            self.conexion = None
            if motivo:
                print("  >> " + motivo, flush=True)
        self.pendiente = bytearray()

    def tomar(self, m, leer=True):
        """Devuelve m muestras y cuántas son del TX (las demás son ceros: el TX no mandó).

        Con leer=False no toma nada (el TX espera): así no transmite hasta que el emulador conoce su frecuencia."""
        falta = 8 * m - len(self.pendiente) if leer else 0
        while self.conexion is not None and falta > 0:
            try:
                trozo = self.conexion.recv(falta)
            except BlockingIOError:
                break
            except OSError:
                trozo = b""
            if not trozo:
                self.cerrar("el TX se desconectó (terminó de transmitir o se cerró su ventana)")
                break
            self.pendiente += trozo
            falta -= len(trozo)
        reales = min(len(self.pendiente) // 8, m)
        x = np.zeros(m, np.complex64)
        x[:reales] = np.frombuffer(self.pendiente, np.complex64, count=reales)
        del self.pendiente[:8 * reales]
        return x, reales


class Enlace:
    """HackRF TX -> aire -> HackRF RX."""

    def __init__(self, args):
        self.args = args
        self.fs = args.muestreo
        self.rng = np.random.default_rng(args.semilla)
        self.fase_aire = self.rng.uniform(0, 2 * np.pi)
        self.fase = 0.0
        self.reloj = Reloj()
        self.inicio = time.perf_counter()
        self.estado = {}
        self.reiniciar_estado()

    def reiniciar_estado(self):
        self.estado = dict(bloques=0, tx_reales=0, tx_potencia=0.0, tx_recortes=0, rx_bloques_senal=0,
                           rx_entrada=0.0, rx_senal=0.0, rx_error=0.0, rx_salida=0.0, rx_saturadas=0,
                           rx_componentes=0, desvio=0.0, fuera_de_banda=False)

    def errores_ppm(self):
        t = time.perf_counter() - self.inicio
        tx = self.args.ppm_tx + self.args.deriva * (1 - math.exp(-t / CALENTAMIENTO_S))
        return tx * 1e-6, self.args.ppm_rx * 1e-6

    def procesar(self, n, entrada, tx, rx, tx_listo):
        """Calcula n muestras del RX. Devuelve los pares (I, Q) de 8 bits que entrega el ADC.

        tx_listo: el emulador ya recibió la frecuencia y las ganancias del TX (antes, el TX espera)."""
        e = self.estado
        e["bloques"] += 1
        vga_tx, lna, vga_rx = ganancias_hackrf(tx, rx)
        eps_tx, eps_rx = self.errores_ppm()

        # 1. DAC del TX (8 bits) y fuga del oscilador local, solo mientras el TX manda muestras
        r = (1 + eps_tx) / (1 + eps_rx)                 # muestras del TX por cada muestra del RX
        x, reales = entrada.tomar(self.reloj.cuantas(n, r), leer=tx_listo)
        if reales:
            iq = x[:reales].view(np.float32)
            e["tx_recortes"] += int(np.count_nonzero(np.abs(iq) > 1))
            x[:reales] = (np.clip(np.round(iq * 127), -127, 127) / 127).astype(np.float32).view(np.complex64)
            x[:reales] += FUGA_LO_TX

        # 2. Potencia del TX: x pasa a estar en raíz de mW
        p_max = TX_POTENCIA_MAX_DBM - (47 - vga_tx) - TX_AMP_DB * (not tx["amp"])
        x *= np.float32(10 ** (p_max / 20))
        if reales:
            e["tx_reales"] += reales
            e["tx_potencia"] += float(np.sum(np.abs(x[:reales]) ** 2))

        # 3. Relojes distintos (muestreo) y 4. aire, sintonía, desvío de portadora y ruido de fase
        y = self.reloj.procesar(x, n, r)
        f_rx = rx["frecuencia"] or tx["frecuencia"] or 915e6
        f_tx = tx["frecuencia"] or f_rx
        desvio = f_tx * (1 + eps_tx) - f_rx * (1 + eps_rx)          # Hz: lo que debería medir el RX
        e["desvio"] = desvio
        e["fuera_de_banda"] = abs(desvio) > self.fs / 2
        paso = 2 * np.pi * desvio / (self.fs * (1 + eps_rx)) + self.rng.normal(0, RUIDO_FASE, n)
        fase = self.fase + np.cumsum(paso)
        self.fase = float(fase[-1] % (2 * np.pi))
        y *= np.exp(1j * (fase + self.fase_aire)).astype(np.complex64) * np.float32(
            0.0 if e["fuera_de_banda"] else 10 ** (-self.args.atenuacion / 20))

        # 5. RX: ruido térmico, ganancias, componente continua y ADC de 8 bits
        ruido_dbm = KT_DBM_HZ + 10 * math.log10(self.fs) + RX_FIGURA_RUIDO_DB[bool(rx["amp"])]
        ruido = self.rng.standard_normal(2 * n, dtype=np.float32).view(np.complex64)
        ruido *= np.float32(math.sqrt(10 ** (ruido_dbm / 10) / 2))
        ganancia = RX_AMP_DB * bool(rx["amp"]) + lna + vga_rx
        g = np.float32(10 ** ((ganancia - RX_ESCALA_ADC_DBM) / 20))
        senal = y * g
        antes_adc = (y + ruido) * g + np.complex64(CONTINUA_RX)
        iq = antes_adc.view(np.float32) * 128
        adc = np.clip(np.round(iq), -128, 127)
        e["rx_saturadas"] += int(np.count_nonzero(np.abs(iq) > 127.5))
        e["rx_componentes"] += 2 * n
        salida = (adc / 128).astype(np.float32).view(np.complex64)
        if reales:
            e["rx_bloques_senal"] += 1
            e["rx_entrada"] += float(np.mean(np.abs(y) ** 2))
            e["rx_senal"] += float(np.mean(np.abs(senal) ** 2))
            e["rx_error"] += float(np.mean(np.abs(salida - senal - np.complex64(CONTINUA_RX)) ** 2))
        e["rx_salida"] += float(np.mean(np.abs(salida) ** 2))
        return adc.astype(np.int8).tobytes()


def db(x):
    return 10 * math.log10(x) if x > 0 else -math.inf


def imprimir_estado(enlace, t, tx, rx, tx_conectado, tx_visto, rx_visto, saltadas):
    e = enlace.estado
    vga_tx, lna, vga_rx = ganancias_hackrf(tx, rx)
    lineas = []
    if e["tx_reales"]:
        lineas.append("TX: transmite en %.3f MHz, %.1f dBm (VGA %d dB, amplificador %s)" % (
            (tx["frecuencia"] or 0) / 1e6, db(e["tx_potencia"] / e["tx_reales"]), vga_tx,
            "SI" if tx["amp"] else "no"))
    elif tx_conectado and not tx_visto:
        lineas.append("TX: conectado, pero no mandó su frecuencia y ganancias (¿es hackrf_tx_archivo_sim.grc?)")
    elif tx_conectado:
        lineas.append("TX: conectado, no está transmitiendo (terminó las pasadas: cerrar su ventana)")
    else:
        lineas.append("TX: apagado")
    if not rx_visto:
        lineas.append("RX: apagado (abrir hackrf_rx_archivo_sim.grc y F6)")
    else:
        texto = "RX: %.3f MHz (LNA %d dB, VGA %d dB, amplificador %s), nivel %.1f dBFS" % (
            (rx["frecuencia"] or 0) / 1e6, lna, vga_rx, "SI" if rx["amp"] else "no", db(e["rx_salida"] / e["bloques"]))
        saturadas = e["rx_saturadas"] / max(e["rx_componentes"], 1)
        if saturadas > 1e-4:
            texto += ", SATURA %.2f %%" % (100 * saturadas)
        lineas.append(texto)
    if e["rx_bloques_senal"]:
        k = e["rx_bloques_senal"]
        if e["fuera_de_banda"]:
            lineas.append("    la señal NO llega: TX y RX están a %.3f MHz de distancia (fuera de banda)" % (
                e["desvio"] / 1e6))
        else:
            s_r = db(e["rx_senal"] / k) - db(e["rx_error"] / k)
            lineas.append("    señal en el RX: %.1f dBm (%.1f dBFS), S/R %.1f dB en 2 MHz, Es/N0 ~ %.1f dB,"
                          " desvío %+.1f kHz" % (db(e["rx_entrada"] / k), db(e["rx_senal"] / k), s_r,
                                                 s_r + 10 * math.log10(enlace.fs / enlace.args.baudios),
                                                 e["desvio"] / 1e3))
            if db(e["rx_entrada"] / k) > RX_MAXIMO_DBM:
                lineas.append("    ¡CUIDADO! una HackRF real se puede dañar con más de %.0f dBm en la entrada:"
                              " usar atenuador o bajar la potencia" % RX_MAXIMO_DBM)
    if e["tx_recortes"]:
        lineas.append("    el DAC del TX recorta %d valores (|I| o |Q| > 1): bajar la amplitud" % e["tx_recortes"])
    for equipo, a in (("TX", tx), ("RX", rx)):
        if a["muestreo"] != enlace.fs:
            lineas.append("    el %s pide %.3f Ms/s pero el emulador trabaja a %.3f Ms/s (--muestreo)" % (
                equipo, a["muestreo"] / 1e6, enlace.fs / 1e6))
    if saltadas:
        lineas.append("    el emulador se atrasó y saltó %.2f s (PC ocupada, o se hizo clic en esta ventana:"
                      " apretar Esc)" % (saltadas / enlace.fs))
    print("[%5.0f s] " % t + ("\n" + " " * 10).join(lineas), flush=True)
    enlace.reiniciar_estado()


def abrir_sockets():
    try:
        servidor_tx = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor_tx.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 18)   # ~16 ms: el TX no se adelanta
        servidor_tx.bind((EMULADOR, PUERTO_TX))
        servidor_tx.listen(1)
        servidor_tx.setblocking(False)
        ajustes = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ajustes.bind((EMULADOR, PUERTO_AJUSTES))
        ajustes.setblocking(False)
    except OSError as error:
        sys.exit("No se pudieron abrir los puertos %d/%d (%s).\n¿Ya hay otro emulador corriendo? Cerrarlo con Ctrl+C."
                 % (PUERTO_TX, PUERTO_AJUSTES, error))
    salida_rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    salida_rx.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 20)
    return servidor_tx, ajustes, salida_rx


def opciones(argv=None):
    p = argparse.ArgumentParser(description="Emulador de dos HackRF One y del aire entre ellas (ver LEEME.md).")
    p.add_argument("--atenuacion", type=float, default=45.0,
                   help="pérdida del aire entre antenas, en dB (45 ~ antenas a unos metros; con cable: 30 del "
                        "atenuador + ~1 del cable; 0 = cable sin atenuador, NUNCA con placas reales)")
    p.add_argument("--ppm-tx", type=float, default=9.0, help="error del cristal del HackRF TX, en ppm")
    p.add_argument("--ppm-rx", type=float, default=-5.0, help="error del cristal del HackRF RX, en ppm")
    p.add_argument("--deriva", type=float, default=1.0,
                   help="cuánto se corre (ppm) el cristal del TX al calentarse (en unos minutos)")
    p.add_argument("--muestreo", type=float, default=2e6, help="muestras por segundo (las de los .grc)")
    p.add_argument("--baudios", type=float, default=250e3, help="símbolos por segundo (solo para mostrar Es/N0)")
    p.add_argument("--cada", type=float, default=2.0, help="cada cuántos segundos muestra el estado")
    p.add_argument("--semilla", type=int, default=None, help="semilla del ruido (para repetir exactamente)")
    return p.parse_args(argv)


def main(argv=None):
    args = opciones(argv)
    servidor_tx, sock_ajustes, salida_rx = abrir_sockets()
    enlace = Enlace(args)
    entrada = EntradaTX()
    ajustes = {k: dict(v) for k, v in AJUSTES_POR_DEFECTO.items()}
    visto = {"tx": -math.inf, "rx": -math.inf}
    print("Emulador de dos HackRF One listo (Ctrl+C para cortar)\n"
          "  aire: %.0f dB de atenuación | cristales: TX %+.1f ppm, RX %+.1f ppm (desvío %+.1f kHz a 915 MHz)\n"
          "  ahora abrir en GNU Radio Companion, con F6: 1) hackrf_simulada/hackrf_rx_archivo_sim.grc\n"
          "                                              2) hackrf_simulada/hackrf_tx_archivo_sim.grc"
          % (args.atenuacion, args.ppm_tx, args.ppm_rx, 915e6 * (args.ppm_tx - args.ppm_rx) * 1e-6 / 1e3),
          flush=True)

    t0 = time.perf_counter()
    hechas = 0              # muestras entregadas desde el comienzo (el reloj del emulador)
    saltadas = 0
    proximo_estado = args.cada
    try:
        while True:
            ahora = time.perf_counter() - t0
            while True:                                  # ajustes nuevos de los .grc
                try:
                    a = leer_ajustes(sock_ajustes.recvfrom(2048)[0])
                except (BlockingIOError, ConnectionResetError):
                    break
                except ValueError:
                    continue
                equipo = a.pop("equipo", "")
                if equipo in ajustes:
                    ajustes[equipo].update(a)
                    visto[equipo] = ahora
            try:                                         # ¿se conectó un TX?
                entrada.nueva(servidor_tx.accept()[0])
            except BlockingIOError:
                pass
            atraso = ahora * args.muestreo - hechas      # muestras que ya deberían haber salido
            if atraso < BLOQUE:
                time.sleep((BLOQUE - atraso) / args.muestreo)
                continue
            if atraso > 0.25 * args.muestreo:            # se trabó (PC ocupada o consola en pausa): saltear
                saltadas += int(atraso) - BLOQUE
                hechas += int(atraso) - BLOQUE
            rx_activo = ahora - visto["rx"] < 1.0
            tx_listo = ahora - visto["tx"] < 1.0
            if rx_activo or entrada.conexion is not None:
                datos = enlace.procesar(BLOQUE, entrada, ajustes["tx"], ajustes["rx"], tx_listo)
                if rx_activo:
                    for k in range(0, len(datos), 2 * MUESTRAS_POR_PAQUETE):
                        try:
                            salida_rx.sendto(datos[k:k + 2 * MUESTRAS_POR_PAQUETE], (EMULADOR, PUERTO_RX))
                        except OSError:
                            pass                         # el RX se acaba de cerrar
            hechas += BLOQUE
            if ahora >= proximo_estado:
                proximo_estado += args.cada
                if enlace.estado["bloques"]:
                    imprimir_estado(enlace, ahora, ajustes["tx"], ajustes["rx"], entrada.conexion is not None,
                                    tx_listo, rx_activo, saltadas)
                saltadas = 0
    except KeyboardInterrupt:
        print("emulador cerrado")
    finally:
        entrada.cerrar()
        for s in (servidor_tx, sock_ajustes, salida_rx):
            s.close()


if __name__ == "__main__":
    main()
