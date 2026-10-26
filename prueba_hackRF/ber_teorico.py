#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BER teórico de 4-QAM (QPSK) con codificación Gray en canal AWGN.

NO necesita GNU Radio: solo numpy (y matplotlib para los gráficos).

Resultados que se calculan (ver INFORME.md, sección 2):

    Pb       = Q( sqrt(2 Eb/N0) ) = 1/2 erfc( sqrt(Eb/N0) )        BER por bit
    Ps       = 2 Q( sqrt(Es/N0) ) - Q^2( sqrt(Es/N0) )             error de símbolo
    Es/N0    = 2 Eb/N0                                              (4-QAM: 2 bits/símbolo)
    PER      = 1 - (1 - Pb)^N                                      error de trama (N bits cubiertos por CRC)
    Pb(phi)  = 1/2 [ Q(sqrt(2Eb/N0)(cos phi - sin phi)) + Q(sqrt(2Eb/N0)(cos phi + sin phi)) ]
                                                                   BER con rotación de fase fija phi SIN corregir

Con codificación diferencial (la que usa el modulador estándar de GNU Radio para resolver la
ambigüedad de 90° del lazo de Costas), con p = Q(sqrt(2 Eb/N0)):

    Pb_dif   = 2 p (1 - p)                                         cada error de símbolo afecta 2 diferencias
    Pb_dif(phi)                                                    idem con fase phi sin corregir (ver función)
    PER_dif  = 1 - (1 - Ps)^(K+1)                                  K símbolos cubiertos (los errores van de a pares)

Además, `--montecarlo` verifica numéricamente Pb y Ps simulando 4-QAM en banda
base (ruido gaussiano, decisión por cuadrantes), y la versión diferencial con la misma
cadena que GNU Radio, independientemente de GNU Radio.

Uso:
    python3 ber_teorico.py                  # tabla + gráfico (resultados/ber_teorico.png)
    python3 ber_teorico.py --montecarlo     # + verificación Monte Carlo
"""
import argparse
import math
import os

import numpy as np


def Q(x):
    """Función Q: cola de la gaussiana estándar."""
    x = np.asarray(x, dtype=float)
    return 0.5 * np.vectorize(math.erfc)(x / math.sqrt(2.0))


def ber_qpsk(ebn0_db):
    """BER de 4-QAM Gray en AWGN: Q(sqrt(2 Eb/N0))."""
    g = 10.0 ** (np.asarray(ebn0_db, dtype=float) / 10.0)
    return Q(np.sqrt(2.0 * g))


def ser_qpsk(ebn0_db):
    """Probabilidad de error de símbolo: 2Q(sqrt(Es/N0)) - Q^2(sqrt(Es/N0)), Es/N0 = 2 Eb/N0."""
    g = 2.0 * 10.0 ** (np.asarray(ebn0_db, dtype=float) / 10.0)
    q = Q(np.sqrt(g))
    return 2.0 * q - q ** 2


def per_from_ber(ber, n_bits):
    """Probabilidad de que una trama de n_bits tenga al menos un error (errores independientes)."""
    return 1.0 - (1.0 - np.asarray(ber, dtype=float)) ** n_bits


def ber_qpsk_phase_error(ebn0_db, phi_deg):
    """BER con un error de fase constante phi SIN corregir."""
    g = 10.0 ** (np.asarray(ebn0_db, dtype=float) / 10.0)
    a = np.sqrt(2.0 * g)
    p = math.radians(phi_deg)
    return 0.5 * (Q(a * (math.cos(p) - math.sin(p))) + Q(a * (math.cos(p) + math.sin(p))))


def _de_error_bits(pa, pb):
    """Bits errados por símbolo (de 2) del 4-QAM con codificación diferencial, dados los errores por eje.

    Un error en un eje gira la decisión +90° (prob. pa) o -90° (prob. pb); en los dos ejes, 180°.
    El decodificador diferencial usa la diferencia entre dos decisiones seguidas: el giro de error es
    d = e[k] - e[k-1] (mod 4); con mapeo Gray, d = ±90° cuesta 1 bit y d = 180° cuesta 2 bits.
    """
    f = [(1 - pa) * (1 - pb), pa * (1 - pb), pa * pb, pb * (1 - pa)]     # P(e = 0, +90, 180, -90)
    g = [sum(f[(d + j) % 4] * f[j] for j in range(4)) for d in range(4)]  # P(d = e[k] - e[k-1])
    return g[1] + g[3] + 2 * g[2]


def ber_deqpsk(ebn0_db):
    """BER de 4-QAM Gray CON codificación diferencial (detección coherente): 2p(1-p), p = Q(sqrt(2Eb/N0))."""
    p = ber_qpsk(ebn0_db)
    return 2.0 * p * (1.0 - p)


def ber_deqpsk_phase_error(ebn0_db, phi_deg):
    """BER de 4-QAM con codificación diferencial y un error de fase constante phi SIN corregir."""
    g = 10.0 ** (np.asarray(ebn0_db, dtype=float) / 10.0)
    a = np.sqrt(2.0 * g)
    p = math.radians(phi_deg)
    pa, pb = Q(a * (math.cos(p) - math.sin(p))), Q(a * (math.cos(p) + math.sin(p)))
    return _de_error_bits(pa, pb) / 2.0


def per_deqpsk(ebn0_db, n_bits, phi_deg=0.0):
    """Prob. de trama errónea con codificación diferencial: la trama de n_bits (n_bits/2 símbolos) llega bien
    solo si no hay ningún error de símbolo en ella ni en el símbolo anterior (los errores vienen de a pares).
    phi_deg: error de fase constante sin corregir (cada eje tiene su propia probabilidad de error)."""
    g = 10.0 ** (np.asarray(ebn0_db, dtype=float) / 10.0)
    a = np.sqrt(2.0 * g)
    p = math.radians(phi_deg)
    pa, pb = Q(a * (math.cos(p) - math.sin(p))), Q(a * (math.cos(p) + math.sin(p)))
    ps = 1.0 - (1.0 - pa) * (1.0 - pb)
    return 1.0 - (1.0 - ps) ** (n_bits / 2.0 + 1.0)


def montecarlo_de(ebn0_db, phi_deg=0.0, n_sym=2_000_000, seed=1):
    """Simula la cadena de GNU Radio: bits -> mapa [0,1,3,2] -> codificador diferencial (mod 4) -> constelación
    -> ruido (+ fase) -> decisión -> decodificador diferencial -> mapa inverso -> bits. Devuelve el BER."""
    rng = np.random.default_rng(seed)
    pts = np.array([-1 - 1j, 1 - 1j, 1 + 1j, -1 + 1j]) / math.sqrt(2.0)
    gray = np.array([0, 1, 3, 2])
    sym = rng.integers(0, 4, n_sym)
    idx = np.cumsum(gray[sym]) % 4                                       # codificador diferencial
    ebn0 = 10.0 ** (ebn0_db / 10.0)
    sig = math.sqrt(1.0 / (4.0 * ebn0))                                  # Es = 1, Eb = 1/2, por componente
    r = pts[idx] * np.exp(1j * math.radians(phi_deg)) + sig * (rng.standard_normal(n_sym)
                                                               + 1j * rng.standard_normal(n_sym))
    dec = np.argmin(np.abs(r[:, None] - pts[None, :]), axis=1)           # decisión por mínima distancia
    d = gray[(dec - np.concatenate(([0], dec[:-1]))) % 4]                # decodificador diferencial + mapa
    bits = lambda s: np.stack([(s >> 1) & 1, s & 1], axis=1)
    return (bits(d[1:]) != bits(sym[1:])).mean()


def required_ebn0_db(target_ber):
    """Eb/N0 [dB] necesario para alcanzar un BER dado (búsqueda por bisección)."""
    lo, hi = -5.0, 20.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if ber_qpsk(mid) > target_ber:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def montecarlo(ebn0_db, n_sym=2_000_000, seed=1):
    """Simula 4-QAM Gray en banda base. Devuelve (BER, SER) medidos."""
    rng = np.random.default_rng(seed)
    b = rng.integers(0, 2, size=(n_sym, 2))
    s = ((1 - 2 * b[:, 0]) + 1j * (1 - 2 * b[:, 1])) / math.sqrt(2.0)   # Es = 1
    ebn0 = 10.0 ** (ebn0_db / 10.0)
    n0 = 1.0 / (2.0 * ebn0)                                              # Eb = 1/2 => N0 = Eb/(Eb/N0)
    sig = math.sqrt(n0 / 2.0)                                            # por componente
    r = s + sig * (rng.standard_normal(n_sym) + 1j * rng.standard_normal(n_sym))
    bh = np.stack([(r.real < 0), (r.imag < 0)], axis=1).astype(int)
    errs = bh != b
    return errs.mean(), errs.any(axis=1).mean()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--montecarlo", action="store_true", help="verifica por simulación en banda base")
    ap.add_argument("--out", default="resultados", help="carpeta de salida")
    ap.add_argument("--no-plot", action="store_true")
    a = ap.parse_args()

    n_per = 32 + 8 * (93 + 4)            # longitud (2x16 b) + payload (93 bytes) + CRC-32 del enlace de grc_estandar/
    print("  Eb/N0[dB]  Es/N0[dB]  Pb coherente  Pb diferencial  Ps (símbolo)  PER dif. (%d bits)" % n_per)
    for e in range(0, 13):
        print("  %7.1f    %7.2f    %.3e     %.3e       %.3e     %.3e" % (
            e, e + 10 * math.log10(2), float(ber_qpsk(e)), float(ber_deqpsk(e)), float(ser_qpsk(e)),
            float(per_deqpsk(e, n_per))))
    print("\nEb/N0 necesario para un BER objetivo (4-QAM coherente sin codificación diferencial):")
    for t in (1e-2, 1e-3, 1e-4, 1e-5, 1e-6):
        print("   BER = %.0e  ->  Eb/N0 = %.2f dB" % (t, required_ebn0_db(t)))

    if a.montecarlo:
        print("\nVerificación Monte Carlo (4-QAM en banda base, 2e6 símbolos por punto):")
        print("  Eb/N0   Pb teórica   Pb simulada   Ps teórica   Ps simulada | diferencial: teórica  simulada  "
              "(con 20° sin corregir: teórica  simulada)")
        for e in (0, 2, 4, 6, 8):
            b, s = montecarlo(e)
            print("  %4d    %.3e    %.3e    %.3e    %.3e  |              %.3e %.3e  "
                  "(                       %.3e %.3e)" % (
                      e, float(ber_qpsk(e)), b, float(ser_qpsk(e)), s, float(ber_deqpsk(e)), montecarlo_de(e),
                      float(ber_deqpsk_phase_error(e, 20)), montecarlo_de(e, 20)))

    if not a.no_plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib no está instalado: se omite el gráfico")
            return
        os.makedirs(a.out, exist_ok=True)
        e = np.linspace(0, 12, 241)
        fig, ax = plt.subplots(figsize=(7.2, 5))
        ax.semilogy(e, ber_qpsk(e), "k--", lw=1.2, label="BER 4-QAM Gray coherente: p = Q(√(2Eb/N0))")
        ax.semilogy(e, ber_deqpsk(e), "k-", lw=2, label="BER con codificación diferencial: 2p(1-p)")
        ax.semilogy(e, ser_qpsk(e), "k:", lw=1.2, label="Prob. error de símbolo")
        for phi, c in ((10, "tab:green"), (20, "tab:orange"), (30, "tab:red")):
            ax.semilogy(e, ber_deqpsk_phase_error(e, phi), color=c, lw=1.2,
                        label="diferencial, error de fase %d° sin corregir" % phi)
        ax.semilogy(e, per_deqpsk(e, n_per), "tab:blue", lw=1.2,
                    label="PER diferencial (%d bits: longitud + payload + CRC)" % n_per)
        ax.set_ylim(1e-7, 1)
        ax.set_xlabel("Eb/N0 [dB]")
        ax.set_ylabel("probabilidad de error")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)
        ax.set_title("4-QAM en AWGN: resultados teóricos")
        fig.tight_layout()
        path = os.path.join(a.out, "ber_teorico.png")
        fig.savefig(path, dpi=140)
        print("\nGráfico guardado en", path)


if __name__ == "__main__":
    main()
