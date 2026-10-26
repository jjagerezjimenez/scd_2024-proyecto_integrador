#!/usr/bin/env python3
"""
Pruebas de los flowgraphs de grc_estandar/ con GNU Radio real (no hay emulador).

    python tests/test_flowgraphs.py        # ~1 minuto

Cada prueba es una función test_*; también funciona con pytest. Los .grc se compilan con grcc en una
carpeta temporal (no se tocan los archivos del proyecto).
"""
import importlib
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")     # los flowgraphs con interfaz corren sin ventana

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRC_DIR = os.path.join(ROOT, "grc_estandar")
sys.path.insert(0, ROOT)
import ber_teorico as teo  # noqa: E402

BUILD = tempfile.mkdtemp(prefix="pruebas_grc_")
_KEEP = []          # flowgraphs con interfaz: se mantienen vivos hasta el final (sus 'Function Probe' siguen leyendo)
GRCS = ("enlace_4qam_tramas.grc", "halfduplex_4qam.grc", "halfduplex_4qam_ber.grc")
MSG = {"A": "Hola, soy el nodo A.", "B": "Hola, soy el nodo B."}      # comienzo de cada mensaje


_MODULES = {}


def compile_grc(name):
    if name in _MODULES:
        return _MODULES[name]
    grcc = shutil.which("grcc") or os.path.join(os.path.dirname(sys.executable), "Scripts", "grcc.exe")
    r = subprocess.run([grcc, "-o", BUILD, os.path.join(GRC_DIR, name)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "error" not in (r.stdout + r.stderr).lower(), r.stdout + r.stderr
    if BUILD not in sys.path:
        sys.path.insert(0, BUILD)
    _MODULES[name] = importlib.import_module(name[:-4])
    return _MODULES[name]


def run_ber(**kw):
    """Corre halfduplex_4qam_ber y devuelve {nodo: (errores, bits, mensajes_ok, primer_mensaje)}."""
    mod = compile_grc("halfduplex_4qam_ber.grc")
    tb = mod.halfduplex_4qam_ber(**kw)
    tb.run()
    out = {}
    for X in "AB":
        err = int(getattr(tb, "rx%s_medidor_ber" % X).total_errors())
        log_ber = getattr(tb, "rx%s_sonda_ber" % X).level()
        bits = err / 10.0 ** log_ber if err else float("nan")      # con 0 errores fec.ber_bf da log10(0) = -inf
        dbg = getattr(tb, "rx%s_mensajes" % X)
        first = ""
        if dbg.num_messages():
            import pmt
            first = bytes(pmt.u8vector_elements(pmt.cdr(dbg.get_message(0)))).decode("utf-8", "replace")
        out[X] = (err, bits, dbg.num_messages(), first)
    return out


def ratio(res, theory):
    errs = sum(res[X][0] for X in "AB")
    bits = sum(res[X][1] for X in "AB")
    return errs / bits / theory


# --------------------------------------------------------------------- pruebas
def test_los_grc_compilan_con_grcc():
    for name in GRCS:
        compile_grc(name)


def test_ber_awgn_coincide_con_la_teoria():
    r = ratio(run_ber(ebn0_db=6.0, muestras=8_000_000), float(teo.ber_deqpsk(6.0)))
    assert 0.95 < r < 1.12, r


def test_ber_con_fase_sin_corregir_coincide_con_la_teoria():
    res = run_ber(ebn0_db=6.0, fase_deg=20.0, costas_bw=0.0, muestras=4_000_000)
    r = ratio(res, float(teo.ber_deqpsk_phase_error(6.0, 20.0)))
    assert 0.97 < r < 1.05, r


def test_costas_corrige_fase_y_desvio_de_frecuencia():
    r = ratio(run_ber(ebn0_db=6.0, fase_deg=20.0, cfo_hz=200.0, muestras=8_000_000), float(teo.ber_deqpsk(6.0)))
    assert 0.95 < r < 1.12, r


def test_cada_nodo_recibe_el_mensaje_del_otro_con_crc_correcto():
    res = run_ber(ebn0_db=12.0, muestras=4_000_000)
    for X, other in (("A", "B"), ("B", "A")):
        err, bits, ok, first = res[X]
        assert ok > 900, (X, ok)                                  # ~1000 tramas por nodo en 4 M muestras
        assert first.startswith(MSG[other]), (X, first)           # recibe lo que transmite el OTRO nodo


def test_misma_semilla_mismo_resultado():
    a = run_ber(ebn0_db=5.0, muestras=2_000_000, semilla=7)
    b = run_ber(ebn0_db=5.0, muestras=2_000_000, semilla=7)
    assert [a[X][:3] for X in "AB"] == [b[X][:3] for X in "AB"], (a, b)


def _run_gui(name, secs, ebn0):
    """Corre un flowgraph con interfaz (sin ventana) unos segundos; devuelve el objeto antes de detenerlo."""
    from PyQt5 import Qt
    mod = compile_grc(name)
    app = Qt.QApplication.instance() or Qt.QApplication([])
    _KEEP.append(app)                      # si se destruye la aplicación Qt, se destruyen las ventanas
    cwd = os.getcwd()
    os.chdir(BUILD)                                               # los archivos de mensajes van a la carpeta temporal
    try:
        tb = getattr(mod, name[:-4])()
        tb.set_ebn0_db(ebn0)
        tb.start()
        tb.flowgraph_started.set()
        t0 = time.time()
        while time.time() - t0 < secs:
            app.processEvents()
            time.sleep(0.05)
        values = {k: v.level() for k, v in vars(tb).items() if k.endswith("sonda_ber") or k == "sonda_ber_acum"}
        tb.stop()
        tb.wait()
        _KEEP.append(tb)
        files = {f: os.path.getsize(f) for f in os.listdir(".") if f.startswith("mensajes_recibidos")}
    finally:
        os.chdir(cwd)
    return values, files


def test_interfaz_half_duplex_corre_sin_trabarse():
    values, files = _run_gui("halfduplex_4qam.grc", 12, 6.0)
    th = float(teo.ber_deqpsk(6.0))
    for k in ("rxA_sonda_ber", "rxB_sonda_ber"):
        assert 0.8 < 10 ** values[k] / th < 1.4, (k, 10 ** values[k] / th)
    assert files.get("mensajes_recibidos_A.txt", 0) > 0 and files.get("mensajes_recibidos_B.txt", 0) > 0, files


def test_interfaz_enlace_simple_corre_sin_trabarse():
    values, files = _run_gui("enlace_4qam_tramas.grc", 8, 6.0)
    r = 10 ** values["sonda_ber_acum"] / float(teo.ber_deqpsk(6.0))
    assert 0.8 < r < 1.4, r
    assert files.get("mensajes_recibidos.txt", 0) > 0, files


def test_teoria_diferencial_coincide_con_monte_carlo():
    for e, phi in ((4.0, 0.0), (4.0, 20.0)):
        th = float(teo.ber_deqpsk_phase_error(e, phi))
        mc = teo.montecarlo_de(e, phi, n_sym=1_000_000)
        assert abs(mc / th - 1) < 0.02, (e, phi, mc, th)
    assert abs(float(teo.ber_deqpsk_phase_error(6.0, 0.0)) - float(teo.ber_deqpsk(6.0))) < 1e-12


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        t0 = time.time()
        try:
            fn()
            print("  OK    %-62s %5.1fs" % (name, time.time() - t0))
        except Exception:  # noqa: BLE001
            failed += 1
            import traceback
            print("  FALLA %-62s" % name)
            traceback.print_exc()
    print("\n%d pruebas, %d fallas" % (len(tests), failed))
    shutil.rmtree(BUILD, ignore_errors=True)
    sys.stdout.flush()
    os._exit(1 if failed else 0)       # os._exit: no espera a los hilos de 'Function Probe' de las interfaces
