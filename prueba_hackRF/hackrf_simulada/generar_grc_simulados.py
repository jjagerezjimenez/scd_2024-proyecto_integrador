"""Genera las versiones SIMULADAS de los .grc de grc_hackrf/, para usarlas con emulador_hackrf.py.

    python hackrf_simulada/generar_grc_simulados.py

Cada .grc simulado es una copia exacta del de grc_hackrf/ (mismos bloques, parámetros y conexiones), salvo:

  * TX: el "Soapy HackRF Sink" se reemplaza por un "TCP Sink" que le manda las muestras al emulador.
  * RX: el "Soapy HackRF Source" se reemplaza por
        Socket PDU (recibe del emulador por UDP) -> PDU to Tagged Stream -> IChar To Complex -> Tag Gate
    El emulador manda pares de bytes (I, Q) de 8 bits, igual que una HackRF por USB; "IChar To Complex" los
    pasa a complejos y "Tag Gate" borra las marcas que pone "PDU to Tagged Stream" en cada paquete de red.
  * Los dos: una variable "ajustes_hackrf" + "Message Strobe" + "Socket PDU" le avisan al emulador, 5 veces
    por segundo, la frecuencia y las ganancias elegidas en la interfaz (lo que el bloque Soapy le pide a la placa).

Todos son bloques estándar de GNU Radio. Los .grc simulados NO se editan a mano: si se cambia un .grc de
grc_hackrf/, se vuelve a correr este script (prueba_completa.py avisa si quedaron desactualizados).
"""
import os
import sys

import yaml

AQUI = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.normpath(os.path.join(AQUI, "..", "grc_hackrf"))

# Direcciones del emulador (todo dentro de la misma PC: 127.0.0.1, sin salir a la red)
EMULADOR = "127.0.0.1"
PUERTO_TX = 5550        # TCP: muestras del TX al emulador
PUERTO_RX = 5551        # UDP: muestras del emulador al RX
PUERTO_AJUSTES = 5552   # UDP: frecuencia y ganancias de los dos .grc al emulador
PERIODO_AJUSTES_MS = 200


def bloque(nombre, tipo, xy, comentario="", **parametros):
    return {"name": nombre, "id": tipo,
            "parameters": {"affinity": "", "alias": "", "comment": comentario, "maxoutbuf": "0", "minoutbuf": "0",
                           **{k: str(v) for k, v in parametros.items()}},
            "states": {"bus_sink": False, "bus_source": False, "bus_structure": None,
                       "coordinate": [int(xy[0]), int(xy[1])], "rotation": 0, "state": "enabled"}}


def variable(nombre, valor, xy, comentario=""):
    b = bloque(nombre, "variable", xy, comentario, value=valor)
    b["parameters"] = {"comment": comentario, "value": valor}
    return b


def nota(nombre, texto, xy):
    b = bloque(nombre, "note", xy, note=texto)
    b["parameters"] = {"alias": "", "comment": "", "note": texto}
    return b


def bajar(grc, desde_y, cuanto):
    """Corre hacia abajo los bloques del dibujo que están debajo de desde_y (deja lugar para los nuevos)."""
    for b in grc["blocks"]:
        x, y = b["states"]["coordinate"]
        if y >= desde_y:
            b["states"]["coordinate"] = [x, y + cuanto]


def sacar(grc, nombre):
    """Quita un bloque y devuelve sus parámetros y su posición."""
    b = next(b for b in grc["blocks"] if b["name"] == nombre)
    grc["blocks"].remove(b)
    return b["parameters"], b["states"]["coordinate"]


def ajustes(grc, equipo, campos, xy):
    """Variable con el texto de los ajustes + Message Strobe + Socket PDU (UDP) hacia el emulador."""
    texto = " ".join("%s=%s" % (k, "%r" if k != "amp" else "%d") for k in campos)
    valores = ", ".join(("bool(%s)" if k == "amp" else "float(%s)") % v for k, v in campos.items())
    x, y = xy
    grc["blocks"] += [
        variable("ajustes_hackrf", '("equipo=%s %s" %% (%s)).encode()' % (equipo, texto, valores), (x, y),
                 "Lo que el bloque Soapy le pediría a la placa (frecuencia, muestreo, ganancias), como texto"),
        bloque("ajustes_periodicos", "blocks_message_strobe", (x + 200, y),
               "Repite los ajustes cada %d ms (si cambian en la interfaz, cambia el mensaje)" % PERIODO_AJUSTES_MS,
               msg="pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(ajustes_hackrf), list(ajustes_hackrf)))",
               period=PERIODO_AJUSTES_MS),
        bloque("ajustes_red", "network_socket_pdu", (x + 440, y), "Manda los ajustes al emulador (UDP)",
               type="UDP_CLIENT", host=EMULADOR, port=PUERTO_AJUSTES, mtu=10000, tcp_no_delay="False"),
    ]
    grc["connections"].append(["ajustes_periodicos", "strobe", "ajustes_red", "pdus"])


def opciones(grc, original):
    p = grc["options"]["parameters"]
    p["id"] += "_sim"
    p["title"] = "[SIMULADA] " + p["title"]
    p["description"] = ("VERSIÓN SIMULADA de grc_hackrf/%s (la genera hackrf_simulada/generar_grc_simulados.py): "
                        "en lugar de una HackRF usa emulador_hackrf.py. %s" % (original, p.get("description", "")))


def aviso(original):
    return ("VERSIÓN SIMULADA, generada por generar_grc_simulados.py a partir de ../grc_hackrf/%s.\n"
            "Es igual al original, salvo los bloques de esta franja: en lugar de la HackRF usa el emulador\n"
            "(python hackrf_simulada/emulador_hackrf.py, corriendo antes de apretar F6).\n"
            "No editar este archivo: cambiar el original y volver a generar." % original)


def simular_tx(grc):
    opciones(grc, "hackrf_tx_archivo.grc")
    for b in grc["blocks"]:                      # el archivo de ejemplo está en grc_hackrf/
        if b["name"] == "archivo" and not os.path.isabs(b["parameters"]["value"]):
            b["parameters"]["value"] = "../grc_hackrf/" + b["parameters"]["value"]
    soapy, (x, y) = sacar(grc, "hackrf_tx")
    bajar(grc, 980, 240)
    grc["blocks"] += [
        nota("nota_simulada", aviso("hackrf_tx_archivo.grc"), (8, 980)),
        bloque("hackrf_tx", "network_tcp_sink", (x, y + 240),
               "HackRF SIMULADA: manda las muestras al emulador, que las toma a %s muestras/s como la placa"
               % soapy["samp_rate"], type="complex", mode="1", addr=EMULADOR, port=PUERTO_TX, vlen=1),
    ]
    ajustes(grc, "tx", {"frecuencia": soapy["center_freq"], "muestreo": soapy["samp_rate"],
                        "vga": soapy["vga"], "amp": soapy["amp"]}, (704, 1000))
    return grc


def simular_rx(grc):
    opciones(grc, "hackrf_rx_archivo.grc")
    soapy, (x, y) = sacar(grc, "hackrf_rx")
    bajar(grc, 180, 240)
    grc["blocks"] += [
        nota("nota_simulada", aviso("hackrf_rx_archivo.grc"), (8, 180)),
        bloque("hackrf_rx_red", "network_socket_pdu", (8, 290), "Recibe del emulador paquetes UDP con I/Q de 8 bits",
               type="UDP_SERVER", host=EMULADOR, port=PUERTO_RX, mtu=10000, tcp_no_delay="False"),
        bloque("hackrf_rx_bytes", "pdu_pdu_to_tagged_stream", (232, 300), "Paquetes de red -> flujo de bytes",
               type="byte", tag="trozo_udp"),
        bloque("hackrf_rx_iq", "blocks_interleaved_char_to_complex", (440, 300),
               "Bytes (I, Q) de 8 bits -> complejo entre -1 y 1, como hace el driver de la HackRF",
               vector_input="False", scale_factor=128),
        bloque("hackrf_rx", "blocks_tag_gate", (x, y + 240), "Borra las marcas de cada paquete de red",
               type="complex", vlen=1, propagate_tags="False", single_key='""'),
    ]
    grc["connections"] += [["hackrf_rx_red", "pdus", "hackrf_rx_bytes", "pdus"],
                           ["hackrf_rx_bytes", "0", "hackrf_rx_iq", "0"],
                           ["hackrf_rx_iq", "0", "hackrf_rx", "0"]]
    ajustes(grc, "rx", {"frecuencia": soapy["center_freq"], "muestreo": soapy["samp_rate"], "lna": soapy["gain"],
                        "vga": soapy["vga"], "amp": soapy["amp"]}, (704, 300))
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
