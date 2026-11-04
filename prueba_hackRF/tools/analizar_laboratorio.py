#!/usr/bin/env python3
"""
Analiza el registro de una prueba de laboratorio (paquetes_recibidos.bin). No modifica ese archivo.

    python tools/analizar_laboratorio.py                                    # grc_hackrf/paquetes_recibidos.bin
    python tools/analizar_laboratorio.py otra/carpeta/paquetes_recibidos.bin --salida resumen.txt

Muestra cuántos paquetes llegaron con CRC correcto, cuántos se perdieron y en qué momento, y si alguno de los paquetes
aceptados difiere del archivo original. El momento de cada pérdida se calcula con la estructura de la pasada:
    [relleno de 2500 bytes | n_paq tramas de N + 18 bytes], a 500 kbit/s.
"""
import argparse
import hashlib
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import reconstruir_archivo as ra  # noqa: E402

N, RELLENO, BITS_POR_SEGUNDO = 200, 2500, 500e3


def analizar(ruta, escribir):
    paquetes = ra.leer_paquetes(ruta, N)
    if not paquetes:
        escribir("No hay paquetes en %s" % ruta)
        return
    d = ra.buscar_descripcion(paquetes)
    if not d:
        escribir("No llegó el paquete que describe el archivo: no se puede seguir.")
        return
    n_paq = d["n_paq"]
    t_trama = (N + 18) * 8 / BITS_POR_SEGUNDO
    t_relleno = RELLENO * 8 / BITS_POR_SEGUNDO
    t_pasada = t_relleno + n_paq * t_trama
    numeros = [k for k, _ in paquetes]
    escribir("Archivo: %s, %d bytes, %d paquetes por pasada" % (d["nombre"], d["tamano"], n_paq))
    escribir("Una trama dura %.3f ms; una pasada, %.3f s" % (t_trama * 1e3, t_pasada))
    escribir("Paquetes recibidos con CRC correcto: %d" % len(paquetes))

    # tiempo de cada paquete dentro de la transmisión; la numeración vuelve a 0 en cada pasada
    pasada, anterior, primero, eventos = 0, None, None, []
    for k in numeros:
        if anterior is not None and k <= anterior:
            pasada += 1
        t = pasada * t_pasada + t_relleno + k * t_trama
        primero = t if primero is None else primero
        if anterior is not None:
            hueco = (k - anterior - 1) % n_paq
            if hueco:
                eventos.append((t - hueco * t_trama - primero, hueco, anterior, k))
        anterior = k
    perdidos = sum(e[1] for e in eventos)
    escribir("Tiempo cubierto por la recepción: %.1f s (%.2f pasadas)" % (t - primero, (t - primero) / t_pasada))
    escribir("Paquetes perdidos: %d  ->  PER medido = %.2e" % (perdidos, perdidos / (perdidos + len(paquetes))))
    escribir("Huecos en la numeración:")
    previo = None
    for t_e, hueco, a, b in eventos:
        desde = "" if previo is None else ", %.3f s después del anterior" % (t_e - previo)
        escribir("  a los %8.3f s: %2d paquetes (%.1f ms), entre el %d y el %d%s" % (t_e, hueco, hueco * t_trama * 1e3, a, b, desde))
        previo = t_e

    # comparación con el archivo original, si está en grc_hackrf/
    original = os.path.join(RAIZ, "grc_hackrf", d["nombre"])
    if os.path.isfile(original):
        with open(original, "rb") as f:
            contenido = f.read()
        distintos = bits = comparados = 0
        for k, datos in paquetes:
            if k >= n_paq - 1:
                continue
            referencia = contenido[k * N:(k + 1) * N]
            referencia += bytes(N - len(referencia))
            comparados += 1
            if datos != referencia:
                distintos += 1
                bits += sum(bin(x ^ y).count("1") for x, y in zip(datos, referencia))
        escribir("Paquetes de datos comparados con el original: %d (%d bits); con contenido distinto: %d; bits distintos: %d" % (
            comparados, comparados * N * 8, distintos, bits))
        unicos = {k: datos for k, datos in reversed(paquetes) if k < n_paq - 1}
        faltan = [k for k in range(n_paq - 1) if k not in unicos]
        armado = b"".join(unicos.get(k, bytes(N)) for k in range(n_paq - 1))[:d["tamano"]]
        escribir("Paquetes del archivo que no llegaron en ninguna pasada: %d" % len(faltan))
        escribir("Huella SHA-256 del archivo armado: %s" % hashlib.sha256(armado).hexdigest())
        escribir("Huella SHA-256 que mandó el transmisor: %s" % d["huella"])
        escribir("Coinciden: %s" % (hashlib.sha256(armado).hexdigest() == d["huella"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ruta", nargs="?", default=os.path.join(RAIZ, "grc_hackrf", "paquetes_recibidos.bin"))
    ap.add_argument("--salida", help="además de mostrar el resumen, lo escribe en este archivo")
    a = ap.parse_args()
    lineas = []

    def escribir(texto):
        print(texto)
        lineas.append(texto)
    analizar(a.ruta, escribir)
    if a.salida:
        with open(a.salida, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    main()
