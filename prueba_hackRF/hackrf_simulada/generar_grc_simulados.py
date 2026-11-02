"""Genera las versiones SIMULADAS de los .grc de grc_hackrf/, para usarlas con emulador_hackrf.py.

    python hackrf_simulada/generar_grc_simulados.py

Cada .grc simulado es una copia exacta del de grc_hackrf/ (mismos bloques, parámetros, conexiones y comentarios
debajo de cada bloque), salvo:

  * TX: el "Soapy HackRF Sink" se reemplaza por un "TCP Sink" que le manda las muestras al emulador. Además,
    "repeticiones" vale 0 (sin fin): con el archivo de ejemplo, 3 pasadas duran 0,3 s y no da tiempo de mirar.
  * RX: el "Soapy HackRF Source" se reemplaza por
        Socket PDU (recibe del emulador por UDP) -> PDU to Tagged Stream -> IChar To Complex -> Tag Gate
    El emulador manda pares de bytes (I, Q) de 8 bits, igual que una HackRF por USB; "IChar To Complex" los
    pasa a complejos y "Tag Gate" borra las marcas que pone "PDU to Tagged Stream" en cada paquete de red.
  * Los dos: una variable "ajustes_hackrf" + "Message Strobe" + "Socket PDU" le avisan al emulador, 5 veces
    por segundo, la frecuencia y las ganancias elegidas en la interfaz (lo que el bloque Soapy le pide a la placa).
    Van en una franja nueva arriba de todo, con una nota de aviso; los comentarios de los bloques nuevos empiezan
    con "HackRF SIMULADA".

Todos son bloques estándar de GNU Radio. Los .grc simulados NO se editan a mano: si se cambia un .grc de
grc_hackrf/, se vuelve a correr este script (prueba_completa.py avisa si quedaron desactualizados).
"""
import os
import sys
import textwrap

import yaml

AQUI = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.normpath(os.path.join(AQUI, "..", "grc_hackrf"))

# Direcciones del emulador (todo dentro de la misma PC: 127.0.0.1, sin salir a la red)
EMULADOR = "127.0.0.1"
PUERTO_TX = 5550        # TCP: muestras del TX al emulador
PUERTO_RX = 5551        # UDP: muestras del emulador al RX
PUERTO_AJUSTES = 5552   # UDP: frecuencia y ganancias de los dos .grc al emulador
PERIODO_AJUSTES_MS = 200

# Lugar en el dibujo para los bloques nuevos (en píxeles del lienzo de GRC)
FRANJA = 304            # alto de la franja que se agrega arriba de todo (aviso + ajustes al emulador)
COLUMNA = 288           # ancho de cada bloque nuevo con su comentario debajo
ANCHO = 46              # caracteres por línea de los comentarios (como en los .grc de grc_hackrf/)


def envolver(texto):
    """Corta cada renglón del comentario a ANCHO caracteres (GRC lo muestra tal cual, debajo del bloque)."""
    lineas = []
    for renglon in texto.split("\n"):
        sangria = "  " if renglon.startswith(("Entra:", "Sale:")) else ""
        lineas += textwrap.wrap(renglon, ANCHO, subsequent_indent=sangria, break_long_words=False) or [""]
    return "\n".join(lineas)


def bloque(nombre, tipo, xy, comentario="", **parametros):
    return {"name": nombre, "id": tipo,
            "parameters": {"affinity": "", "alias": "", "comment": envolver(comentario), "maxoutbuf": "0",
                           "minoutbuf": "0", **{k: str(v) for k, v in parametros.items()}},
            "states": {"bus_sink": False, "bus_source": False, "bus_structure": None,
                       "coordinate": [int(xy[0]), int(xy[1])], "rotation": 0, "state": "enabled"}}


def variable(nombre, valor, xy, comentario=""):
    b = bloque(nombre, "variable", xy, comentario, value=valor)
    b["parameters"] = {"comment": envolver(comentario), "value": valor}
    return b


def nota(nombre, texto, xy):
    """Nota de GRC: el texto completo va en el comentario, que GRC muestra debajo del bloque."""
    b = bloque(nombre, "note", xy, note=texto.replace("\n", " "))
    b["parameters"] = {"alias": "", "comment": envolver(texto), "note": texto.replace("\n", " ")}
    return b


def correr(grc, dx, dy, desde_y=None):
    """Corre los bloques (dx, dy) para dejar lugar a los nuevos; con desde_y, solo los que están más abajo."""
    for b in [grc["options"]] + grc["blocks"]:
        x, y = b["states"]["coordinate"]
        if desde_y is None or y >= desde_y:
            b["states"]["coordinate"] = [x + dx, y + dy]


def sacar(grc, nombre):
    """Quita un bloque y devuelve sus parámetros y su posición."""
    b = next(b for b in grc["blocks"] if b["name"] == nombre)
    grc["blocks"].remove(b)
    return b["parameters"], b["states"]["coordinate"]


def franja(grc, original, equipo, campos, extra=""):
    """Franja nueva arriba de todo: aviso + variable con el texto de los ajustes + Message Strobe + Socket PDU (UDP)
    que le avisan al emulador la frecuencia y las ganancias elegidas en la ventana."""
    correr(grc, 0, FRANJA)
    texto = " ".join("%s=%s" % (k, "%r" if k != "amp" else "%d") for k in campos)
    valores = ", ".join(("bool(%s)" if k == "amp" else "float(%s)") % v for k, v in campos.items())
    grc["blocks"] += [
        nota("nota_simulada", aviso(original, extra), (8, 8)),
        variable("ajustes_hackrf", '("equipo=%s %s" %% (%s)).encode()' % (equipo, texto, valores),
                 (8 + COLUMNA, 16),
                 "HackRF SIMULADA: texto con lo que el bloque Soapy le pediría a la placa (frecuencia, muestreo y "
                 "ganancias). Cambia cuando se mueve un control de la ventana."),
        bloque("ajustes_periodicos", "blocks_message_strobe", (8 + 2 * COLUMNA, 16),
               "HackRF SIMULADA: repite el texto de los ajustes cada %d ms, como un mensaje (si cambia un "
               "control, cambia el mensaje).\n"
               "Entra: nada (es una fuente de mensajes).\n"
               "Sale: mensajes (PDU) con el texto de los ajustes." % PERIODO_AJUSTES_MS,
               msg="pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(ajustes_hackrf), list(ajustes_hackrf)))",
               period=PERIODO_AJUSTES_MS),
        bloque("ajustes_red", "network_socket_pdu", (8 + 3 * COLUMNA, 16),
               "HackRF SIMULADA: manda cada mensaje por UDP al emulador (%s:%d), que así usa la frecuencia y "
               "las ganancias elegidas.\n"
               "Entra: mensajes (PDU).\n"
               "Sale: nada (van por la red, sin salir de la PC)." % (EMULADOR, PUERTO_AJUSTES),
               type="UDP_CLIENT", host=EMULADOR, port=PUERTO_AJUSTES, mtu=10000, tcp_no_delay="False"),
    ]
    grc["connections"].append(["ajustes_periodicos", "strobe", "ajustes_red", "pdus"])


def opciones(grc, original):
    p = grc["options"]["parameters"]
    p["id"] += "_sim"
    p["title"] = "[SIMULADA] " + p["title"]
    p["description"] = ("VERSIÓN SIMULADA de grc_hackrf/%s (la genera hackrf_simulada/generar_grc_simulados.py): "
                        "en lugar de una HackRF usa emulador_hackrf.py. %s" % (original, p.get("description", "")))


def aviso(original, extra=""):
    return ("VERSIÓN SIMULADA, generada por generar_grc_simulados.py a partir de ../grc_hackrf/%s.\n"
            "Es igual al original, salvo los bloques que dicen \"HackRF SIMULADA\": en lugar de la placa usa el "
            "emulador (python hackrf_simulada/emulador_hackrf.py, corriendo antes de apretar F6).%s\n"
            "No editar este archivo: cambiar el original y volver a generar." % (original, extra))


def simular_tx(grc):
    opciones(grc, "hackrf_tx_archivo.grc")
    for b in grc["blocks"]:
        if b["name"] == "archivo" and not os.path.isabs(b["parameters"]["value"]):
            b["parameters"]["value"] = "../grc_hackrf/" + b["parameters"]["value"]   # el ejemplo está ahí
        if b["name"] == "repeticiones":
            # Con el archivo de ejemplo, 3 pasadas duran 0,3 s: no da tiempo de mirar las gráficas.
            # En el ensayo se transmite sin fin y se cierra la ventana del TX cuando se terminó de revisar.
            b["parameters"]["value"] = "0"
    soapy, (x, y) = sacar(grc, "hackrf_tx")
    franja(grc, "hackrf_tx_archivo.grc", "tx", {"frecuencia": soapy["center_freq"], "muestreo": soapy["samp_rate"],
                                                "vga": soapy["vga"], "amp": soapy["amp"]},
           "\nAdemás transmite sin fin (repeticiones = 0): cerrar la ventana cuando se terminó de revisar.")
    grc["blocks"].append(
        bloque("hackrf_tx", "network_tcp_sink", (x, y + FRANJA),
               "HackRF SIMULADA: en lugar de la placa, manda las muestras por TCP al emulador (%s:%d), que "
               "las toma a 2 M muestras/s (samp_rate), como la placa.\n"
               "Entra: complejos, con I y Q entre -1 y 1.\n"
               "Sale: nada en el flowgraph: van al emulador." % (EMULADOR, PUERTO_TX),
               type="complex", mode="1", addr=EMULADOR, port=PUERTO_TX, vlen=1))
    return grc


def simular_rx(grc):
    opciones(grc, "hackrf_rx_archivo.grc")
    soapy, (x, y) = sacar(grc, "hackrf_rx")
    franja(grc, "hackrf_rx_archivo.grc", "rx", {"frecuencia": soapy["center_freq"], "muestreo": soapy["samp_rate"],
                                                "lna": soapy["gain"], "vga": soapy["vga"], "amp": soapy["amp"]})
    # La placa se reemplaza por 4 bloques en fila: se corre a la derecha todo lo que está desde la nota de entrada
    # hacia abajo (la cadena del receptor), y los bloques nuevos ocupan el lugar que queda a la izquierda.
    y += FRANJA
    nota_entrada = next(b for b in grc["blocks"] if b["name"] == "nota_entrada")
    correr(grc, 3 * COLUMNA, 0, desde_y=nota_entrada["states"]["coordinate"][1])
    grc["blocks"] += [
        bloque("hackrf_rx_red", "network_socket_pdu", (x, y - 24),
               "HackRF SIMULADA: recibe del emulador paquetes UDP (puerto %d) con 4096 muestras I/Q de 8 bits, "
               "como las que manda una HackRF por USB.\n"
               "Entra: nada (los paquetes llegan por la red).\n"
               "Sale: mensajes (PDU) de 8192 bytes." % PUERTO_RX,
               type="UDP_SERVER", host=EMULADOR, port=PUERTO_RX, mtu=10000, tcp_no_delay="False"),
        bloque("hackrf_rx_bytes", "pdu_pdu_to_tagged_stream", (x + COLUMNA, y),
               "HackRF SIMULADA: pasa cada mensaje a un flujo de bytes y marca dónde empieza cada paquete de red "
               "(etiqueta trozo_udp).\n"
               "Entra: mensajes (PDU).\n"
               "Sale: bytes (I, Q, I, Q, ...) con etiquetas.",
               type="byte", tag="trozo_udp"),
        bloque("hackrf_rx_iq", "blocks_interleaved_char_to_complex", (x + 2 * COLUMNA, y),
               "HackRF SIMULADA: junta cada par de bytes (I, Q) en un complejo y lo divide por 128 (queda entre "
               "-1 y 1), como hace el driver de la HackRF.\n"
               "Entra: bytes con signo, de a pares (I, Q).\n"
               "Sale: complejos a 2 M muestras/s (samp_rate).",
               vector_input="False", scale_factor=128),
        bloque("hackrf_rx", "blocks_tag_gate", (x + 3 * COLUMNA, y),
               "HackRF SIMULADA: borra las etiquetas de cada paquete de red (el receptor no las necesita).\n"
               "Entra: complejos.\n"
               "Sale: los mismos complejos, sin etiquetas.",
               type="complex", vlen=1, propagate_tags="False", single_key='""'),
    ]
    grc["connections"] += [["hackrf_rx_red", "pdus", "hackrf_rx_bytes", "pdus"],
                           ["hackrf_rx_bytes", "0", "hackrf_rx_iq", "0"],
                           ["hackrf_rx_iq", "0", "hackrf_rx", "0"]]
    return grc


class _Dumper(yaml.SafeDumper):
    pass


# Como GRC: listas cortas en una línea ([x, y], conexiones) y textos de varias líneas con "|"
_Dumper.add_representer(list, lambda d, x: d.represent_sequence(
    "tag:yaml.org,2002:seq", x, flow_style=all(not isinstance(i, (list, dict)) for i in x)))
_Dumper.add_representer(str, lambda d, s: d.represent_scalar(
    "tag:yaml.org,2002:str", s, style="|" if "\n" in s else None))


def generar(nombre):
    """Devuelve (ruta del .grc simulado, texto que le corresponde)."""
    with open(os.path.join(ORIGEN, nombre + ".grc"), encoding="utf-8") as f:
        grc = yaml.safe_load(f)
    grc = simular_tx(grc) if "_tx_" in nombre else simular_rx(grc)
    texto = yaml.dump(grc, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10000)
    return os.path.join(AQUI, nombre + "_sim.grc"), texto


NOMBRES = ["hackrf_tx_archivo", "hackrf_rx_archivo"]


def main():
    for nombre in NOMBRES:
        ruta, texto = generar(nombre)
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        print("generado", os.path.relpath(ruta, os.path.join(AQUI, "..")))


if __name__ == "__main__":
    sys.exit(main())
