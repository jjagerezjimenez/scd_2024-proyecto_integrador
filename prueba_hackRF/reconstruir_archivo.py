#!/usr/bin/env python3
"""
Reconstruye el archivo recibido con grc_hackrf/hackrf_rx_archivo.grc.

    python reconstruir_archivo.py                                  # lee grc_hackrf/paquetes_recibidos.bin
    python reconstruir_archivo.py otra/carpeta/paquetes_recibidos.bin

El receptor guarda en paquetes_recibidos.bin, uno detrás de otro, los paquetes con CRC correcto:
[número de paquete (2 bytes) | N bytes]. El último paquete de cada pasada describe el archivo:
    ARCHIVO|nombre|tamaño|N|paquetes|huella SHA-256|
Este script ordena los paquetes por número (los repetidos de otras pasadas se descartan), arma el archivo, lo
recorta a su tamaño original y compara su huella SHA-256 con la que mandó el transmisor. También cuenta los
paquetes perdidos (saltos en la numeración) y estima el PER. Solo usa la biblioteca estándar de Python.
"""
import argparse
import hashlib
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
POR_DEFECTO = os.path.join(AQUI, "grc_hackrf", "paquetes_recibidos.bin")


def leer_paquetes(ruta, n):
    """Lista de (número, datos) en el orden en que llegaron."""
    with open(ruta, "rb") as f:
        crudo = f.read()
    t = n + 2
    return [(crudo[i] * 256 + crudo[i + 1], crudo[i + 2:i + t]) for i in range(0, len(crudo) - t + 1, t)]


def buscar_descripcion(paquetes):
    """Datos del paquete final 'ARCHIVO|...' (o None si no llegó ninguno)."""
    for numero, datos in paquetes:
        if not datos.startswith(b"ARCHIVO|"):
            continue
        campos = datos.split(b"|")
        try:
            # el transmisor recorta el nombre a 40 bytes: si cortó una letra con acento, se descarta
            d = {"nombre": campos[1].decode("utf-8", "ignore"), "tamano": int(campos[2]), "n": int(campos[3]),
                 "n_paq": int(campos[4]), "huella": campos[5].decode("ascii")}
        except (IndexError, ValueError, UnicodeDecodeError):
            continue
        if numero == d["n_paq"] - 1 and len(d["huella"]) == 64:
            return d
    return None


def contar_perdidos(numeros, n_paq):
    """Paquetes que faltan entre cada par de paquetes recibidos seguidos (la numeración vuelve a 0 en cada pasada)."""
    return sum((b - a - 1) % n_paq for a, b in zip(numeros, numeros[1:]))


def reconstruir(ruta=POR_DEFECTO, n=200, carpeta=None):
    """Arma el archivo y devuelve un resumen (dict)."""
    paquetes = leer_paquetes(ruta, n)
    carpeta = carpeta or os.path.dirname(os.path.abspath(ruta))
    info = {"recibidos": len(paquetes), "descripcion": buscar_descripcion(paquetes), "salida": None,
            "identico": None, "faltan": [], "perdidos": 0, "per": float("nan")}
    if not paquetes:
        return info
    d = info["descripcion"]
    if d:
        if d["n"] != n:
            raise SystemExit("El transmisor usó N = %d bytes por paquete: correr con --n %d" % (d["n"], d["n"]))
        n_paq, nombre = d["n_paq"], "recibido_" + os.path.basename(d["nombre"])
    else:                                  # sin descripción no se conoce el nombre ni el tamaño exacto
        n_paq, nombre = max(k for k, _ in paquetes) + 2, "recibido_sin_descripcion.bin"
    unicos = {}
    for numero, datos in paquetes:
        if numero < n_paq - 1:
            unicos.setdefault(numero, datos)          # primera copia que llegó de cada paquete
    info["faltan"] = [k for k in range(n_paq - 1) if k not in unicos]
    info["perdidos"] = contar_perdidos([k for k, _ in paquetes], n_paq)
    info["per"] = info["perdidos"] / (info["perdidos"] + len(paquetes))
    contenido = b"".join(unicos.get(k, bytes(n)) for k in range(n_paq - 1))
    if d:
        contenido = contenido[:d["tamano"]]
        info["identico"] = hashlib.sha256(contenido).hexdigest() == d["huella"]
    info["salida"] = os.path.join(carpeta, nombre)
    with open(info["salida"], "wb") as f:
        f.write(contenido)
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ruta", nargs="?", default=POR_DEFECTO, help="paquetes_recibidos.bin del receptor")
    ap.add_argument("--n", type=int, default=200, help="bytes de datos por paquete (variable N de los .grc)")
    ap.add_argument("--carpeta", help="dónde escribir el archivo reconstruido (por defecto, junto al .bin)")
    a = ap.parse_args()
    if not os.path.isfile(a.ruta):
        sys.exit("No existe %s: primero hay que recibir con hackrf_rx_archivo.grc" % a.ruta)
    info = reconstruir(a.ruta, a.n, a.carpeta)
    print("Paquetes con CRC correcto: %d" % info["recibidos"])
    if not info["recibidos"]:
        sys.exit("No llegó ningún paquete correcto.")
    d = info["descripcion"]
    if d:
        print("Archivo: %s (%d bytes, %d paquetes por pasada)" % (d["nombre"], d["tamano"], d["n_paq"]))
    else:
        print("AVISO: no llegó el paquete que describe el archivo (nombre, tamaño, huella).")
    print("Paquetes perdidos (saltos en la numeración): %d  ->  PER medido = %.2e" % (info["perdidos"], info["per"]))
    if info["faltan"]:
        print("FALTAN %d paquetes (quedaron en cero): %s%s" % (len(info["faltan"]), info["faltan"][:20],
                                                              " ..." if len(info["faltan"]) > 20 else ""))
        print("  -> transmitir más pasadas (parámetro 'repeticiones') o mejorar la señal.")
    print("Escrito: %s" % info["salida"])
    if info["identico"] is True:
        print("Huella SHA-256 IGUAL a la del transmisor: el archivo llegó idéntico.")
    elif info["identico"] is False:
        print("Huella SHA-256 DISTINTA: el archivo no está completo o tiene errores.")
    return 0 if info["identico"] else 1


if __name__ == "__main__":
    sys.exit(main())
