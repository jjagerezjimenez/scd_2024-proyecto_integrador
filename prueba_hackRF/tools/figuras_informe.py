#!/usr/bin/env python3
"""
Genera las figuras propias del informe en figuras_informe/:

    python tools/figuras_informe.py               # esquemas y flowgraphs
    python tools/figuras_informe.py esquemas      # solo los esquemas (matplotlib)
    python tools/figuras_informe.py flowgraphs    # solo los dibujos de los .grc

Los esquemas se dibujan con matplotlib. Los flowgraphs se dibujan con las mismas clases que usa GNU Radio Companion,
sin abrir ventanas: los bloques se acomodan más juntos, sin comentarios y sin los bloques de gráficos y sondas, para
que se lean en una hoja A4. Los .grc del proyecto no se modifican: se trabaja sobre copias temporales.
"""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "figuras_informe")

AZUL, AZUL_F = "#0b3a6b", "#e8eef5"
NARANJA, NARANJA_F = "#b85c00", "#fdecd8"
GRIS, GRIS_F = "#555555", "#efefef"
NODO_A, NODO_B = "#1f4fb4", "#c62828"


# ------------------------------------------------------------------------------------------------- esquemas
def preparar():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
    plt.rcParams["font.size"] = 8.5
    return plt


def lienzo(plt, ancho, alto):
    fig, ax = plt.subplots(figsize=(ancho, alto))
    ax.set_xlim(0, ancho)
    ax.set_ylim(0, alto)
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def caja(ax, x, y, w, h, texto, borde=AZUL, relleno=AZUL_F, letra=8.0, negrita=False, color=None):
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.04", fc=relleno, ec=borde, lw=0.9))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=letra, color=color or "#111111",
            fontweight="bold" if negrita else "normal", linespacing=1.15)


def flecha(ax, x0, y0, x1, y1, color="#222222", lw=1.0, estilo="-|>", rad=0.0):
    from matplotlib.patches import FancyArrowPatch
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=estilo, mutation_scale=8, lw=lw, color=color,
                                 shrinkA=0, shrinkB=0, connectionstyle="arc3,rad=%g" % rad))


def guardar(fig, plt, nombre):
    os.makedirs(SALIDA, exist_ok=True)
    ruta = os.path.join(SALIDA, nombre)
    fig.savefig(ruta, dpi=220, facecolor="white")
    plt.close(fig)
    print("escrito", os.path.relpath(ruta, RAIZ))


def constelacion(plt):
    """Los cuatro símbolos y los cuatro giros de fase de la codificación diferencial."""
    import math
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.2, 2.75))
    fig.subplots_adjust(0.05, 0.03, 0.99, 0.90, wspace=0.12)
    r = 1 / math.sqrt(2)
    for ax in (a, b):
        ax.set_xlim(-1.45, 1.45)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(plt.Circle((0, 0), 1, fill=False, ec="#bbbbbb", lw=0.8, ls="--"))
        ax.annotate("", (1.4, 0), (-1.4, 0), arrowprops=dict(arrowstyle="-|>", color=GRIS, lw=0.8))
        ax.annotate("", (0, 1.28), (0, -1.28), arrowprops=dict(arrowstyle="-|>", color=GRIS, lw=0.8))
        ax.text(1.38, 0.07, "I", color=GRIS, ha="right")
        ax.text(0.07, 1.2, "Q", color=GRIS)
    a.set_title("Símbolos de 4-QAM (energía 1)", fontsize=9, color=AZUL, fontweight="bold")
    for sx in (1, -1):
        for sy in (1, -1):
            a.plot(sx * r, sy * r, "o", color=AZUL, ms=7)
            a.text(sx * (r + 0.07), sy * (r + 0.16), "%s0,707 %s 0,707j" % ("+" if sx > 0 else "−", "+" if sy > 0 else "−"),
                   ha="left" if sx > 0 else "right", va="center", fontsize=7.6)
    b.set_title("Cambio de fase según los dos bits", fontsize=9, color=AZUL, fontweight="bold")
    giros = [(r, r, "00: sin giro", "left", 0.07, 0.16),
             (-r, r, "01: +90°", "right", -0.07, 0.16),
             (-r, -r, "11: 180°", "right", -0.07, -0.16),
             (r, -r, "10: −90°", "left", 0.07, -0.16)]
    for x, y, t, ha, dx, dy in giros:
        b.plot(x, y, "o", color=AZUL if t.startswith("00") else "#9db4cd", ms=7)
        b.text(x + dx, y + dy, t, ha=ha, va="center", fontsize=8.2)
    b.text(r + 0.15, r - 0.17, "símbolo\nanterior", ha="left", va="center", fontsize=7.2, color=GRIS, linespacing=1.05)
    flecha(b, r - 0.06, r, -r + 0.07, r, color=NARANJA, lw=1.1, rad=0.25)
    flecha(b, r - 0.05, r - 0.05, -r + 0.05, -r + 0.05, color=NARANJA, lw=1.1)
    flecha(b, r, r - 0.07, r, -r + 0.07, color=NARANJA, lw=1.1, rad=-0.25)
    guardar(fig, plt, "constelacion.png")


def trama(plt):
    """Formato de la trama en simulación y en laboratorio, y estructura de una pasada."""
    fig, ax = lienzo(plt, 7.1, 3.05)
    def fila(y, titulo, campos, x0=1.28, ancho=5.75, h=0.38):
        ax.text(x0 - 0.07, y + h / 2, titulo, ha="right", va="center", fontsize=8.2, fontweight="bold", color=AZUL)
        total = sum(c[1] for c in campos)
        x = x0
        for c in campos:
            w = ancho * c[1] / total
            if c[0] == "...":                # sin caja: las tramas del medio no se dibujan
                ax.text(x + w / 2, y + h / 2, "...", ha="center", va="center", fontsize=10)
            else:
                borde, relleno = c[2] if len(c) > 2 else (AZUL, AZUL_F)
                caja(ax, x, y, w, h, c[0], borde=borde, relleno=relleno, letra=c[3] if len(c) > 3 else 7.6)
            x += w
    lab = (NARANJA, NARANJA_F)
    gris = (GRIS, GRIS_F)
    fila(2.42, "Simulación", [("Preámbulo\n64 bits", 2.2), ("Longitud\n16 bits", 1.3), ("Longitud\n16 bits", 1.3),
                              ("Datos: 93 bytes (mensaje de texto)", 5.0), ("CRC-32\n32 bits", 1.3)])
    fila(1.62, "Laboratorio", [("Preámbulo\n64 bits", 2.2), ("Longitud\n16 bits", 1.3), ("Longitud\n16 bits", 1.3),
                               ("Número\n2 bytes", 1.3, lab), ("Datos: 200 bytes del archivo", 3.7), ("CRC-32\n32 bits", 1.3)])
    ax.annotate("", (1.28 + 5.75 * 4.8 / 11.1, 1.53), (1.28, 1.53), arrowprops=dict(arrowstyle="|-|,widthA=0.25,widthB=0.25", lw=0.8, color=GRIS))
    ax.text(1.28 + 5.75 * 2.4 / 11.1, 1.42, "Encabezado: 12 bytes", ha="center", va="center", fontsize=7.4, color=GRIS)
    fila(0.48, "Pasada\n(laboratorio)", [("Relleno al azar\n2500 bytes", 3.2, gris), ("Trama 0", 1.5), ("Trama 1", 1.5), ("...", 1.0),
                                         ("Última trama\nde datos", 1.8), ("Descripción:\nnombre, tamaño,\nSHA-256", 2.1, lab, 7.0)], h=0.5)
    ax.text(1.28 + 5.75 / 2, 0.24, "La pasada se repite: si una trama se pierde, se recupera en otra vuelta.", ha="center", va="center", fontsize=7.8, color=GRIS)
    guardar(fig, plt, "trama.png")


def halfduplex(plt):
    """Dos nodos que comparten un canal por turnos."""
    fig, ax = lienzo(plt, 7.1, 3.25)
    y1, y2, h = 2.38, 1.5, 0.52
    caja(ax, 0.1, y1, 1.1, h, "Transmisor\nnodo A", borde=NODO_A, relleno="#e6ecfa", negrita=True)
    caja(ax, 0.1, y2, 1.1, h, "Transmisor\nnodo B", borde=NODO_B, relleno="#fbe9e9", negrita=True)
    caja(ax, 1.55, 1.64, 0.92, 1.12, "Stream Mux\n\narma\nlos turnos", letra=7.8)
    caja(ax, 2.8, 1.84, 1.2, 0.72, "Canal compartido\nfase + ruido", borde=GRIS, relleno=GRIS_F, letra=7.8)
    caja(ax, 4.33, 1.64, 0.92, 1.12, "Stream Demux\n\nreparte\nlos turnos", letra=7.8)
    caja(ax, 5.98, y1, 1.02, h, "Receptor\nnodo B", borde=NODO_B, relleno="#fbe9e9", negrita=True)
    caja(ax, 5.98, y2, 1.02, h, "Receptor\nnodo A", borde=NODO_A, relleno="#e6ecfa", negrita=True)
    flecha(ax, 1.2, y1 + h / 2, 1.55, y1 + h / 2 - 0.02, color=NODO_A)
    flecha(ax, 1.2, y2 + h / 2, 1.55, y2 + h / 2 + 0.02, color=NODO_B)
    flecha(ax, 2.47, 2.2, 2.8, 2.2)
    flecha(ax, 4.0, 2.2, 4.33, 2.2)
    flecha(ax, 5.25, y1 + h / 2 - 0.02, 5.98, y1 + h / 2, color=NODO_A)
    flecha(ax, 5.25, y2 + h / 2 + 0.02, 5.98, y2 + h / 2, color=NODO_B)
    ax.text(5.61, y1 + h / 2 + 0.07, "turno de A", ha="center", fontsize=7, color=NODO_A)
    ax.text(5.61, y2 + h / 2 - 0.15, "turno de B", ha="center", fontsize=7, color=NODO_B)
    # línea de tiempo
    x, y, alto = 0.75, 0.62, 0.42
    esc = 0.56
    ax.text(0.1, y + alto / 2, "Canal:", va="center", fontsize=8.2, fontweight="bold", color=AZUL)
    for rep in range(2):
        for nombre, dur, borde, relleno in (("Transmite A", 4.1, NODO_A, "#e6ecfa"), ("", 0.5, GRIS, "#ffffff"),
                                            ("Transmite B", 4.1, NODO_B, "#fbe9e9"), ("", 0.5, GRIS, "#ffffff")):
            w = dur * esc * 0.52
            caja(ax, x, y, w, alto, nombre, borde=borde, relleno=relleno, letra=7.6)
            x += w
    ax.annotate("guarda 0,5 ms", (0.75 + 4.1 * esc * 0.52 + 0.04, y), (1.75, 0.3), fontsize=7.2, color=GRIS, ha="center", va="center",
                arrowprops=dict(arrowstyle="-", color=GRIS, lw=0.6))
    ax.text(0.75 + 2.05 * esc * 0.52, y + alto + 0.1, "4,1 ms", ha="center", va="center", fontsize=7.2, color=GRIS)
    ax.text(5.0, 0.3, "Nunca transmiten los dos a la vez y ningún nodo se escucha a sí mismo.", ha="center", va="center", fontsize=7.8, color=GRIS)
    guardar(fig, plt, "sistema_halfduplex.png")


def cadena(plt):
    """Cadena de transmisión y de recepción; en naranja, lo que se agrega para el laboratorio."""
    fig, ax = lienzo(plt, 7.1, 3.85)
    lab = dict(borde=NARANJA, relleno=NARANJA_F)
    def fila(y, cajas, x0=0.06, sep=0.13, h=0.56, ancho=6.98):
        w = (ancho - sep * (len(cajas) - 1)) / len(cajas)
        x = x0
        pos = []
        for texto, es_lab in cajas:
            caja(ax, x, y, w, h, texto, letra=7.2, **(lab if es_lab else {}))
            pos.append((x, w))
            x += w + sep
        for (xa, wa), (xb, _) in zip(pos, pos[1:]):
            flecha(ax, xa + wa, y + h / 2, xb, y + h / 2)
        return pos, y, h
    ax.text(0.06, 3.68, "Transmisor", fontsize=9, fontweight="bold", color=AZUL, va="center")
    tx, y_tx, h = fila(3.03, [("Archivo o\nmensaje", False), ("Número de\npaquete", True), ("CRC-32", False), ("Encabezado:\npreámbulo y\nlongitud", False),
                              ("Relleno al\ncomienzo de\nla pasada", True), ("4-QAM\ndiferencial\ny filtro RRC", False), ("Corrimiento\n+400 kHz", True), ("HackRF\nTX", True)])
    caja(ax, 0.06, 2.34, 6.98, 0.4, "Canal.  Simulación: rotación de fase + ruido blanco (AWGN).   Laboratorio: el aire, a 915 MHz, unos 40 cm.", borde=GRIS, relleno=GRIS_F, letra=7.8)
    xs, ws = tx[-1]
    flecha(ax, xs + ws / 2, y_tx, xs + ws / 2, 2.74)
    ax.text(0.66, 2.12, "Receptor", fontsize=9, fontweight="bold", color=AZUL, va="center")
    r1, y_r1, _ = fila(1.32, [("HackRF\nRX", True), ("Corrimiento\n−400 kHz y\nfiltro de canal", True), ("Control de\nganancia\n(AGC)", True),
                              ("Corrección\ngruesa de\nfrecuencia (FLL)", True), ("Filtro\nadaptado\nRRC", False), ("Sincronismo\nde símbolo", False), ("Lazo de Costas\n(fase fina)", False)])
    r2, y_r2, _ = fila(0.5, [("Decisión\ndel símbolo", False), ("Decodificación\ndiferencial", False), ("Mapa Gray\ny bits", False), ("Detector de\ntrama (preámbulo\ny longitud)", False),
                             ("Verificación\nCRC-32: descarta\nerróneas", False), ("Ordena por\nnúmero y verifica\nSHA-256", True), ("Archivo o\nmensaje", False)])
    x_r, w_r = r1[0]
    flecha(ax, x_r + w_r / 2, 2.34, x_r + w_r / 2, y_r1 + h)
    # de la fila 1 a la fila 2
    xa, wa = r1[-1]
    xb, wb = r2[0]
    y_medio = y_r2 + h + 0.13
    ax.plot([xa + wa / 2, xa + wa / 2, xb + wb / 2], [y_r1, y_medio, y_medio], color="#222222", lw=1.0)
    flecha(ax, xb + wb / 2, y_medio, xb + wb / 2, y_r2 + h)
    # referencias
    caja(ax, 1.55, 0.09, 0.26, 0.2, "", letra=7)
    ax.text(1.87, 0.19, "Igual en simulación y en laboratorio", va="center", fontsize=7.8)
    caja(ax, 4.35, 0.09, 0.26, 0.2, "", letra=7, **lab)
    ax.text(4.67, 0.19, "Se agrega para el laboratorio", va="center", fontsize=7.8)
    guardar(fig, plt, "cadena_tx_rx.png")


def montaje(plt):
    """Disposición de los equipos en la prueba de laboratorio."""
    from matplotlib.patches import Arc
    fig, ax = lienzo(plt, 7.1, 2.75)
    caja(ax, 2.5, 1.93, 2.1, 0.74, "Una computadora con GNU Radio\nhackrf_tx_archivo.grc\nhackrf_rx_archivo.grc", borde=GRIS, relleno=GRIS_F, letra=7.8)
    caja(ax, 0.65, 0.62, 1.45, 0.62, "HackRF One\ntransmisor", negrita=True)
    caja(ax, 5.0, 0.62, 1.45, 0.62, "HackRF One\nreceptor", negrita=True)
    ax.plot([2.5, 1.38, 1.38], [2.24, 2.24, 1.24], color=GRIS, lw=1.2)
    ax.plot([4.6, 5.72, 5.72], [2.24, 2.24, 1.24], color=GRIS, lw=1.2)
    ax.text(1.88, 2.31, "USB", fontsize=7.4, color=GRIS, ha="center")
    ax.text(5.22, 2.31, "USB", fontsize=7.4, color=GRIS, ha="center")
    # antenas
    xa, xb = 2.1, 5.0
    for x, s in ((xa, 1), (xb, -1)):
        ax.plot([x, x + s * 0.18, x + s * 0.18], [0.93, 0.93, 1.5], color=AZUL, lw=1.6)
    # ondas
    centro_tx = xa + 0.18
    for r in (0.24, 0.42, 0.6):
        ax.add_patch(Arc((centro_tx, 1.38), r * 2, r * 2, theta1=-36, theta2=36, color=NARANJA, lw=1.0))
    # distancia
    ax.annotate("", (xb - 0.18, 0.6), (centro_tx, 0.6), arrowprops=dict(arrowstyle="<|-|>", color="#222222", lw=0.8))
    ax.text((centro_tx + xb - 0.18) / 2, 0.72, "unos 40 cm", ha="center", fontsize=8.2, fontweight="bold")
    ax.text((centro_tx + xb - 0.18) / 2 + 0.2, 1.38, "915 MHz", ha="center", va="center", fontsize=8.2, color=NARANJA, fontweight="bold")
    ax.text(1.38, 0.32, "VGA 20 dB · amplificador apagado\namplitud digital 0,5", ha="center", va="center", fontsize=7.6)
    ax.text(5.72, 0.32, "LNA 40 dB · VGA 40 dB\namplificador apagado", ha="center", va="center", fontsize=7.6)
    guardar(fig, plt, "montaje_laboratorio.png")


def esquemas():
    plt = preparar()
    constelacion(plt)
    trama(plt)
    halfduplex(plt)
    cadena(plt)
    montaje(plt)


# ------------------------------------------------------------------------------------------------ flowgraphs
TX = {"sec_fuente": (10, 70), "sec_paquetes": (160, 78), "paquete": (365, 78), "crc": (578, 70), "encabezado": (782, 0), "trama": (995, 78),
      "datos_fuente": (10, 170), "datos_paquetes": (160, 178),
      "relleno_fuente": (10, 290), "pasada": (150, 298), "limite": (315, 305), "modulador": (512, 285), "desplazar": (724, 300),
      "ajuste_amplitud": (912, 305), "hackrf_tx": (1052, 300)}

RX = {"hackrf_rx": (35, 18), "entrada": (250, 26), "trasladar": (400, 2), "agc": (612, 0), "fll": (760, 0), "filtro_adaptado": (985, 0),
      "sinc_simbolo": (35, 215), "costas": (385, 230), "decisor": (585, 255), "dec_diferencial": (790, 250), "mapa_gray": (960, 255), "a_bits": (1090, 255),
      "detector_trama": (35, 430), "a_bytes": (290, 435), "crc": (470, 430), "archivo_paquetes": (680, 395), "solo_datos": (680, 490), "archivo_datos": (820, 490)}

HD = {"txA_fuente": (10, 58), "txA_a_paquetes": (160, 66), "txA_crc": (362, 58), "txA_encabezado": (565, 0), "txA_trama": (775, 66), "txA_modulador": (985, 50), "txA_vs": (1195, 72),
      "canal_tx_A": (10, 215), "silencio_1": (10, 280), "canal_tx_B": (10, 345), "silencio_3": (10, 410),
      "turnos": (178, 275), "acelerador": (378, 295), "fase": (535, 305), "ruido_awgn": (510, 395), "suma_ruido": (680, 300), "conmutador_rx": (770, 275),
      "osc_rxB": (1010, 190), "rxB_vs_entrada": (1185, 197), "guarda_1": (1010, 268), "osc_rxA": (1010, 340), "rxA_vs_entrada": (1185, 347), "guarda_3": (1010, 430)}


def preparar_grc():
    """Carga las clases del lienzo de GNU Radio Companion sin abrir la aplicación."""
    base = os.path.dirname(sys.executable)
    extra = [base, os.path.join(base, "Library", "mingw-w64", "bin"), os.path.join(base, "Library", "usr", "bin"),
             os.path.join(base, "Library", "bin"), os.path.join(base, "Scripts")]
    os.environ["PATH"] = os.pathsep.join(extra + [os.environ.get("PATH", "")])
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Gtk
    from gnuradio import gr
    from gnuradio.grc.gui.canvas import flowgraph as lienzo_grc

    class SinAplicacion:
        def get_windows(self):
            return []
    Gtk.Application.get_default = staticmethod(lambda: SinAplicacion())
    lienzo_grc._ContextMenu = lambda main_window: None
    from gnuradio.grc.gui.Platform import Platform
    from gnuradio.grc.gui import Actions
    for accion in Actions.actions.get_actions().values():
        if accion.preference_name and isinstance(accion.default, bool):
            accion.set_active(accion.default)         # sin la aplicación quedan todas activas
    Actions.TOGGLE_SHOW_BLOCK_COMMENTS.set_active(False)
    plataforma = Platform(version=gr.version(), version_parts=(gr.major_version(), gr.api_version(), gr.minor_version()),
                          prefs=gr.prefs(), install_prefix=gr.prefix())
    plataforma.build_library()
    return plataforma


def dibujar_flowgraph(plataforma, rel, lugares, nombre, cambios=None, escala=2.0):
    """Dibuja solo los bloques de `lugares`, en esas posiciones, con sus conexiones."""
    import cairo
    import yaml
    ruta = os.path.join(RAIZ, rel)
    with open(ruta, encoding="utf-8") as f:
        grc = yaml.safe_load(f)
    for b in grc["blocks"]:
        if b["name"] in lugares:
            b["states"]["coordinate"] = list(lugares[b["name"]])
        for clave, valor in (cambios or {}).get(b["name"], {}).items():
            b["parameters"][clave] = valor
    falta = set(lugares) - {b["name"] for b in grc["blocks"]}
    if falta:
        raise SystemExit("bloques que no existen en %s: %s" % (rel, sorted(falta)))
    with tempfile.TemporaryDirectory() as tmp:
        copia = os.path.join(tmp, nombre + ".grc")
        with open(copia, "w", encoding="utf-8") as f:
            yaml.safe_dump(grc, f, allow_unicode=True, sort_keys=False)
        anterior = os.getcwd()
        os.chdir(os.path.dirname(ruta))          # para que el .grc encuentre el archivo que lee al evaluarse
        try:
            fg = plataforma.make_flow_graph(copia)
            fg.update()
        finally:
            os.chdir(anterior)
    def se_ve(e):
        if e.is_block:
            return e.name in lugares
        return e.is_connection and e.source_block.name in lugares and e.sink_block.name in lugares
    fg._elements_to_draw[:] = [e for e in fg._elements_to_draw if se_ve(e)]
    # primero en un lienzo de prueba, para que GRC calcule el tamaño de cada bloque
    prueba = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10))
    fg.draw(prueba)
    x0, y0, x1, y1 = fg.get_extents()
    margen = 8
    w, h = int((x1 - x0 + 2 * margen) * escala), int((y1 - y0 + 2 * margen) * escala)
    sup = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(sup)
    cr.set_source_rgb(1, 1, 1)
    cr.paint()
    cr.scale(escala, escala)
    cr.translate(margen - x0, margen - y0)
    cr.set_line_width(2.0)
    fg.draw(cr)
    os.makedirs(SALIDA, exist_ok=True)
    png = os.path.join(SALIDA, nombre + ".png")
    sup.write_to_png(png)
    print("escrito", os.path.relpath(png, RAIZ), "(%d x %d)" % (w, h))


def flowgraphs():
    plataforma = preparar_grc()
    prueba_texto = {"archivo": {"value": "archivo_a_enviar.txt"}, "repeticiones": {"value": "0"}}
    dibujar_flowgraph(plataforma, "grc_hackrf/hackrf_tx_archivo.grc", TX, "flowgraph_tx", prueba_texto)
    dibujar_flowgraph(plataforma, "grc_hackrf/hackrf_rx_archivo.grc", RX, "flowgraph_rx")
    dibujar_flowgraph(plataforma, "grc_estandar/halfduplex_4qam.grc", HD, "flowgraph_halfduplex")


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if que in ("todo", "esquemas"):
        esquemas()
    if que in ("todo", "flowgraphs"):
        flowgraphs()
