#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Barrido de BER vs Eb/N0 del enlace half-duplex (grc_estandar/halfduplex_4qam_ber.grc) para distintas
condiciones de canal, y comparación con la teoría.

El flowgraph es SOLO bloques estándar de GNU Radio. Este script es una herramienta de medición:
  1) compila el .grc con grcc (en build/), así el .grc es la única fuente del enlace;
  2) lo ejecuta una vez por punto (condición de canal, Eb/N0) con los parámetros correspondientes;
  3) suma los resultados de los DOS receptores (nodo A y nodo B) y calcula:

    BER medido   = errores de bit / bits comparados (fec.ber_bf, flujo alineado con el primer preámbulo)
    IC 95 %      = intervalo de Wilson
    BER teórico  = según la condición (ver ber_teorico.py): 4-QAM con codificación diferencial, 2p(1-p)
    PER medido   = 1 - (tramas con CRC correcto / tramas enviadas)
    PER teórico  = 1 - (1 - Ps)^(K+1), K = símbolos cubiertos por longitud + payload + CRC

La cantidad de muestras de cada punto se elige para acumular ~`--target-errors` errores
(acotada entre --min-samples y --max-samples).

Uso:
    python run_ber_sweep.py --quick                          # prueba rápida
    python run_ber_sweep.py                                  # barrido completo
    python run_ber_sweep.py --scenarios awgn --ebn0 0:10:1   # solo AWGN
    python run_ber_sweep.py --out otra_carpeta               # sin pisar resultados/
    python run_ber_sweep.py --plot-only                      # rehacer gráficos desde el CSV
"""
import argparse
import csv
import math
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ber_teorico as teo  # noqa: E402

GRC = os.path.join(HERE, "grc_estandar", "halfduplex_4qam_ber.grc")
BUILD = os.path.join(HERE, "build")
SPS, RANURA, GUARDA = 4, 2048, 256                       # deben coincidir con las variables del .grc
FRAC_NODO = RANURA / (2.0 * (RANURA + GUARDA))           # fracción del canal que usa cada nodo
BITS_POR_MUESTRA = 2 * FRAC_NODO * 2.0 / SPS             # bits recibidos por muestra de canal (A + B)

# Condiciones de canal (kw = parámetros del .grc; theory = curva de referencia)
SCENARIOS = {
    "awgn": dict(
        label="AWGN ideal",
        kw=dict(),
        theory=lambda e: teo.ber_deqpsk(e)),
    "fase_sin_sync": dict(
        label="AWGN + fase 20° SIN corregir",
        kw=dict(fase_deg=20.0, costas_bw=0.0),            # Costas con ancho de banda 0 = no corrige la fase
        theory=lambda e: teo.ber_deqpsk_phase_error(e, 20.0), phi=20.0),
    "fase_con_sync": dict(
        label="AWGN + fase 20° con lazo de Costas",
        kw=dict(fase_deg=20.0),
        theory=lambda e: teo.ber_deqpsk(e)),
    "cfo_pll": dict(
        label="AWGN + fase 20° + CFO 200 Hz con lazo de Costas",
        kw=dict(fase_deg=20.0, cfo_hz=200.0),
        theory=lambda e: teo.ber_deqpsk(e)),
}

FIELDS = ["scenario", "ebn0_db", "samples", "bits", "bit_errors", "ber", "ber_lo", "ber_hi", "ber_theory", "ratio",
          "ber_A", "ber_B", "frames_sent", "crc_ok", "crc_ok_with_errors", "per", "per_theory"]


def wilson(k, n, z=1.96):
    """Intervalo de confianza de Wilson para una proporción k/n."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def parse_range(txt):
    a, b, s = (float(v) for v in txt.split(":"))
    n = int(round((b - a) / s)) + 1
    return [round(a + i * s, 6) for i in range(n)]


def build_flowgraph():
    """Compila el .grc con grcc y devuelve el módulo Python generado."""
    os.makedirs(BUILD, exist_ok=True)
    grcc = shutil.which("grcc") or os.path.join(os.path.dirname(sys.executable), "Scripts", "grcc.exe")
    subprocess.run([grcc, "-o", BUILD, GRC], check=True, stdout=subprocess.DEVNULL)
    sys.path.insert(0, BUILD)
    import halfduplex_4qam_ber
    return halfduplex_4qam_ber


def run_point(mod, ebn0, samples, seed, kw):
    """Ejecuta el flowgraph y devuelve {nodo: (errores, bits, tramas_crc_ok, crc_ok_pero_distintas)}."""
    import pmt
    tb = mod.halfduplex_4qam_ber(ebn0_db=ebn0, muestras=int(samples), semilla=seed, **kw)
    tb.run()
    res = {}
    for X in "AB":
        err = int(getattr(tb, "rx%s_medidor_ber" % X).total_errors())
        log_ber = getattr(tb, "rx%s_sonda_ber" % X).level()
        if err:
            bits = err / 10.0 ** log_ber
        else:                                # con 0 errores fec.ber_bf da log10(0) = -inf: se estiman los bits
            bits = samples * FRAC_NODO * 2.0 / SPS
        # tramas que el CRC aceptó: ¿el mensaje es exactamente el que transmitió el otro nodo?
        dbg = getattr(tb, "rx%s_mensajes" % X)
        esperado = bytes(getattr(tb, "payload_%s" % ("B" if X == "A" else "A")))
        distintas = sum(bytes(pmt.u8vector_elements(pmt.cdr(dbg.get_message(i)))) != esperado
                        for i in range(dbg.num_messages()))
        res[X] = (err, bits, dbg.num_messages(), distintas)
    return res


def frame_info(mod):
    """Bits por trama de cada nodo y bits cubiertos por longitud + payload + CRC (para el PER teórico)."""
    tb = mod.halfduplex_4qam_ber(muestras=1)
    out = {}
    for X in "AB":
        L = getattr(tb, "L_%s" % X)
        out[X] = (8 * (8 + 4 + L + 4), 32 + 8 * (L + 4))
    return out


def run_sweep(args):
    mod = build_flowgraph()
    finfo = frame_info(mod)
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "resultados_ber.csv")
    keep = args.resume and os.path.exists(path)
    done = set()
    if keep:
        with open(path) as f:
            done = {(r["scenario"], round(float(r["ebn0_db"]), 6)) for r in csv.DictReader(f)}
    fout = open(path, "a" if keep else "w", newline="")
    w = csv.DictWriter(fout, fieldnames=FIELDS)
    if not keep:
        w.writeheader()
    for name in args.scenarios:
        sc = SCENARIOS[name]
        print("\n== %s ==" % sc["label"])
        print("  Eb/N0   muestras    BER medido  [IC 95%]              BER teórico  medido/teórico  "
              "A        B         PER med.  PER teór.")
        for e in args.ebn0:
            if (name, round(e, 6)) in done:
                print("  %5.1f  (ya medido, se omite)" % e)
                continue
            th = float(sc["theory"](e))
            samples = int(min(max(args.target_errors / (th * BITS_POR_MUESTRA), args.min_samples), args.max_samples))
            t0 = time.time()
            res = run_point(mod, e, samples, args.seed, sc["kw"])
            errs = sum(res[X][0] for X in "AB")
            bits = sum(res[X][1] for X in "AB")
            ok = sum(res[X][2] for X in "AB")
            bad = sum(res[X][3] for X in "AB")
            sent = sum(samples * FRAC_NODO / (finfo[X][0] / 2 * SPS) for X in "AB")
            ber = errs / bits if bits else float("nan")
            lo, hi = wilson(errs, bits)
            per = max(0.0, 1.0 - ok / sent)
            per_th = float(sum(teo.per_deqpsk(e, finfo[X][1], sc.get("phi", 0.0)) for X in "AB") / 2)
            w.writerow(dict(scenario=name, ebn0_db=e, samples=samples, bits=round(bits), bit_errors=errs, ber=ber,
                            ber_lo=lo, ber_hi=hi, ber_theory=th, ratio=ber / th if th > 0 else float("nan"),
                            ber_A=res["A"][0] / res["A"][1], ber_B=res["B"][0] / res["B"][1],
                            frames_sent=round(sent), crc_ok=ok, crc_ok_with_errors=bad, per=per, per_theory=per_th))
            fout.flush()
            print("  %5.1f  %9d   %.3e  [%.2e, %.2e]   %.3e      %6.3f       %.2e %.2e  %.3f    %.3f   (%.0fs)" % (
                e, samples, ber, lo, hi, th, ber / th, res["A"][0] / res["A"][1], res["B"][0] / res["B"][1],
                per, per_th, time.time() - t0))
            sys.stdout.flush()
    fout.close()
    print("\nResultados guardados en", path)
    return path


def equivalent_loss_db(theory, ebn0, ber):
    """Corrimiento en dB entre la curva teórica y el BER medido: el Eb/N0 que la teoría
    necesitaría para dar `ber`, menos el Eb/N0 realmente usado (>0 = pérdida)."""
    lo, hi = -10.0, 30.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if float(theory(mid)) > ber:
            lo = mid
        else:
            hi = mid
    return ebn0 - 0.5 * (lo + hi)


def summary(path, out, min_errors=100):
    """Tabla resumen por condición: pérdida equivalente (ponderada por errores) respecto de la teoría,
    separada en Eb/N0 bajo (0-1 dB) y Eb/N0 medio-alto (>= 2 dB)."""
    rows = load_csv(path)

    def wavg(name, lo, hi):
        rs = [r for r in rows if r["scenario"] == name and lo <= r["ebn0_db"] <= hi
              and r["bit_errors"] >= min_errors and r["ber"] > 0]
        if not rs:
            return None
        th = SCENARIOS[name]["theory"]
        w = [r["bit_errors"] for r in rs]
        loss = sum(a * equivalent_loss_db(th, r["ebn0_db"], r["ber"]) for a, r in zip(w, rs)) / sum(w)
        ratio = sum(a * r["ratio"] for a, r in zip(w, rs)) / sum(w)
        return loss, ratio, len(rs)

    lines = ["| Condición de canal | pérdida a 0–1 dB [dB] | pérdida a 2–10 dB [dB] | medido/teórico medio (2–10 dB) | puntos (2–10 dB) |",
             "|---|---:|---:|---:|---:|"]
    for name in SCENARIOS:
        lo, hi = wavg(name, 0, 1), wavg(name, 2, 100)
        f = lambda v: "%+.2f" % v[0] if v else "–"
        lines.append("| %s | %s | %s | %s | %s |" % (
            SCENARIOS[name]["label"], f(lo), f(hi), "%.3f" % hi[1] if hi else "–", hi[2] if hi else 0))
    text = "\n".join(lines)
    with open(os.path.join(out, "resumen_perdidas.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print("\nResumen (solo puntos con >= %d errores; pérdida = Eb/N0 extra que la teoría necesitaría para dar el BER medido):\n%s" % (min_errors, text))


def load_csv(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if k != "scenario":
                r[k] = float(v)
    return rows


def plot(path, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib/numpy no están instalados: se omiten los gráficos")
        return
    rows = load_csv(path)
    by = {}
    for r in rows:
        by.setdefault(r["scenario"], []).append(r)
    ee = np.linspace(0, 12, 241)
    colors = {"awgn": "tab:blue", "fase_sin_sync": "tab:red", "fase_con_sync": "tab:green", "cfo_pll": "tab:purple"}
    marks = {"awgn": "o", "fase_sin_sync": "s", "fase_con_sync": "^", "cfo_pll": "D"}

    def draw(ax, names, ylim=(1e-6, 1)):
        for n in names:
            if n not in by:
                continue
            rs = sorted(by[n], key=lambda r: r["ebn0_db"])
            x = [r["ebn0_db"] for r in rs]
            y = [r["ber"] for r in rs]
            lo = [max(r["ber"] - r["ber_lo"], 0) for r in rs]
            hi = [max(r["ber_hi"] - r["ber"], 0) for r in rs]
            th = SCENARIOS[n]["theory"]
            ax.semilogy(ee, th(ee), "-", color=colors[n], lw=1.3, alpha=0.8)
            ax.errorbar(x, y, yerr=[lo, hi], fmt=marks[n], color=colors[n], ms=5, capsize=2,
                        label="%s (medido)" % SCENARIOS[n]["label"])
        ax.set_ylim(*ylim)
        ax.set_xlim(0, 12)
        ax.set_xlabel("Eb/N0 [dB]")
        ax.set_ylabel("BER")
        ax.grid(True, which="both", alpha=0.3)

    os.makedirs(out, exist_ok=True)
    # 1) solo AWGN, con la curva del 4-QAM coherente sin codificación diferencial como referencia
    fig, ax = plt.subplots(figsize=(7.2, 5))
    draw(ax, ["awgn"])
    ax.plot([], [], "-", color="tab:blue", label="teoría con cod. diferencial: 2p(1-p)")
    ax.semilogy(ee, teo.ber_qpsk(ee), "--", color="gray", lw=1.0, label="teoría sin cod. diferencial: p = Q(√(2Eb/N0))")
    ax.legend(fontsize=9)
    ax.set_title("BER medido en GNU Radio vs teoría (4-QAM, AWGN)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "ber_awgn_medido_vs_teorico.png"), dpi=140)
    # 2) todas las condiciones
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    draw(ax, list(SCENARIOS), ylim=(1e-6, 1))
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title("BER para distintas condiciones de canal (línea = teoría)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "ber_condiciones_de_canal.png"), dpi=140)
    # 3) PER (error de trama) AWGN
    if "awgn" in by:
        rs = sorted(by["awgn"], key=lambda r: r["ebn0_db"])
        fig, ax = plt.subplots(figsize=(7.2, 5))
        ax.semilogy([r["ebn0_db"] for r in rs], [r["per_theory"] for r in rs], "-", color="tab:orange",
                    label="PER teórico: 1-(1-Ps)^(K+1)")
        ax.semilogy([r["ebn0_db"] for r in rs], [max(r["per"], 1e-6) for r in rs], "o", color="tab:orange",
                    label="PER medido (CRC-32 incorrecto o trama perdida)")
        ax.set_ylim(1e-4, 1.5)
        ax.set_xlim(0, 12)
        ax.set_xlabel("Eb/N0 [dB]")
        ax.set_ylabel("tasa de error de trama")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=9)
        ax.set_title("Detección de errores con CRC-32: tasa de tramas erróneas")
        fig.tight_layout()
        fig.savefig(os.path.join(out, "per_awgn_medido_vs_teorico.png"), dpi=140)
    print("Gráficos guardados en", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scenarios", default="awgn,fase_sin_sync,fase_con_sync,cfo_pll",
                    help="lista separada por comas: " + ", ".join(SCENARIOS))
    ap.add_argument("--ebn0", default="0:10:1", help="rango inicio:fin:paso en dB")
    ap.add_argument("--target-errors", type=int, default=400)
    ap.add_argument("--min-samples", type=float, default=4e6)
    ap.add_argument("--max-samples", type=float, default=2e8)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(HERE, "resultados"))
    ap.add_argument("--quick", action="store_true", help="menos muestras: resultados más ruidosos pero rápidos")
    ap.add_argument("--resume", action="store_true", help="agregar al CSV y omitir los puntos ya medidos")
    ap.add_argument("--plot-only", action="store_true")
    args = ap.parse_args()
    args.scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    for s in args.scenarios:
        if s not in SCENARIOS:
            ap.error("escenario desconocido: " + s)
    args.ebn0 = parse_range(args.ebn0)
    if args.quick:
        args.target_errors, args.min_samples, args.max_samples = 100, 1e6, 2e7
    csv_path = os.path.join(args.out, "resultados_ber.csv")
    if not args.plot_only:
        csv_path = run_sweep(args)
    plot(csv_path, args.out)
    summary(csv_path, args.out)


if __name__ == "__main__":
    main()
