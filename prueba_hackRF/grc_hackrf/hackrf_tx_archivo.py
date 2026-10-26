#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: HackRF TX: transmisión de un archivo (4-QAM, bloques estándar)
# Author: Juan Gerez
# Description: Transmite un archivo en paquetes numerados (CRC-32, preámbulo y longitud) con 4-QAM diferencial por un HackRF; solo bloques estándar de GNU Radio
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import soapy
import os, math, hashlib, random
import sip
import threading
import time



class hackrf_tx_archivo(gr.top_block, Qt.QWidget):

    def __init__(self, archivo='archivo_a_enviar.txt', repeticiones=3):
        gr.top_block.__init__(self, "HackRF TX: transmisión de un archivo (4-QAM, bloques estándar)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("HackRF TX: transmisión de un archivo (4-QAM, bloques estándar)")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "hackrf_tx_archivo")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Parameters
        ##################################################
        self.archivo = archivo
        self.repeticiones = repeticiones

        ##################################################
        # Variables
        ##################################################
        self.encontrado = encontrado = os.path.isfile(archivo)
        self.contenido = contenido = list(open(archivo, "rb").read()) if encontrado else list(("No se encontro el archivo " + archivo).encode())
        self.N = N = 200
        self.n_datos = n_datos = (len(contenido) + N - 1) // N
        self.n_paq = n_paq = n_datos + 1
        self.bytes_trama = bytes_trama = N + 18
        self.W = W = 2500
        self.sps = sps = 8
        self.samp_rate = samp_rate = 2e6
        self.nombre = nombre = os.path.basename(archivo) if encontrado else "ERROR_archivo_no_encontrado.txt"
        self.huella = huella = hashlib.sha256(bytes(contenido)).hexdigest()
        self.bytes_pasada = bytes_pasada = W + n_paq * bytes_trama
        self.total_bytes = total_bytes = repeticiones * bytes_pasada + W if repeticiones > 0 else 2**62
        self.enviados = enviados = 0
        self.duracion_pasada = duracion_pasada = bytes_pasada * 8 / 2 / (samp_rate / sps)
        self.descripcion = descripcion = list(b"ARCHIVO|" + nombre.encode()[:40] + ("|%d|%d|%d|%s|" % (len(contenido), N, n_paq, huella)).encode())
        self.vga_tx = vga_tx = 20
        self.secuencia = secuencia = [b for i in range(n_paq) for b in ((i // 256) % 256, i % 256)]
        self.relleno = relleno = list(random.Random(1).randbytes(W))
        self.qpsk = qpsk = digital.constellation_rect([-0.707-0.707j, 0.707-0.707j, +0.707+0.707j, -0.707+0.707j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.lbl_pasadas = lbl_pasadas = (min(enviados, total_bytes - W) / bytes_pasada)
        self.lbl_paquetes = lbl_paquetes = "%d (%.2f s cada pasada)" % (n_paq, duracion_pasada)
        self.lbl_huella = lbl_huella = huella[:16] + "..."
        self.lbl_archivo = lbl_archivo = "%s (%d bytes)" % (nombre, len(contenido))
        self.freq_mhz = freq_mhz = 915
        self.formato_trama = formato_trama = digital.header_format_default(digital.packet_utils.default_access_code,0, 1)
        self.f_offset = f_offset = 400e3
        self.excess_bw = excess_bw = 0.35
        self.dispositivo = dispositivo = ""
        self.datos = datos = contenido + [0] * (n_datos * N - len(contenido)) + (descripcion + [0] * N)[:N]
        self.amplitud = amplitud = 0.5
        self.amp_tx = amp_tx = False

        ##################################################
        # Blocks
        ##################################################

        self._vga_tx_range = qtgui.Range(0, 47, 1, 20, 150)
        self._vga_tx_win = qtgui.RangeWidget(self._vga_tx_range, self.set_vga_tx, "Ganancia TX (VGA) [dB]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._vga_tx_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.limite = blocks.head(gr.sizeof_char*1, total_bytes)
        self._freq_mhz_tool_bar = Qt.QToolBar(self)
        self._freq_mhz_tool_bar.addWidget(Qt.QLabel("Frecuencia [MHz]" + ": "))
        self._freq_mhz_line_edit = Qt.QLineEdit(str(self.freq_mhz))
        self._freq_mhz_tool_bar.addWidget(self._freq_mhz_line_edit)
        self._freq_mhz_line_edit.editingFinished.connect(
            lambda: self.set_freq_mhz(eng_notation.str_to_num(str(self._freq_mhz_line_edit.text()))))
        self.top_grid_layout.addWidget(self._freq_mhz_tool_bar, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._amplitud_range = qtgui.Range(0.05, 0.7, 0.05, 0.5, 150)
        self._amplitud_win = qtgui.RangeWidget(self._amplitud_range, self.set_amplitud, "Amplitud digital (pico < 1)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._amplitud_win, 0, 3, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        _amp_tx_check_box = Qt.QCheckBox("Amplificador TX (+14 dB)")
        self._amp_tx_choices = {True: True, False: False}
        self._amp_tx_choices_inv = dict((v,k) for k,v in self._amp_tx_choices.items())
        self._amp_tx_callback = lambda i: Qt.QMetaObject.invokeMethod(_amp_tx_check_box, "setChecked", Qt.Q_ARG("bool", self._amp_tx_choices_inv[i]))
        self._amp_tx_callback(self.amp_tx)
        _amp_tx_check_box.stateChanged.connect(lambda i: self.set_amp_tx(self._amp_tx_choices[bool(i)]))
        self.top_grid_layout.addWidget(_amp_tx_check_box, 0, 2, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.sec_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, 2, "packet_len")
        self.sec_fuente = blocks.vector_source_b(secuencia, True, 1, [])
        self.relleno_fuente = blocks.vector_source_b(relleno, True, 1, [])
        self.pasada = blocks.stream_mux(gr.sizeof_char*1, [W, n_paq * bytes_trama])
        self.paquete = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.modulador = digital.generic_mod(
            constellation=qpsk,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=excess_bw,
            verbose=False,
            log=False,
            truncate=False)
        self._lbl_pasadas_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.2f' % x:
            self._lbl_pasadas_formatter = lambda x: '%.2f' % x
        else:
            self._lbl_pasadas_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_pasadas_tool_bar.addWidget(Qt.QLabel("Pasadas enviadas: "))
        self._lbl_pasadas_label = Qt.QLabel(str(self._lbl_pasadas_formatter(self.lbl_pasadas)))
        self._lbl_pasadas_tool_bar.addWidget(self._lbl_pasadas_label)
        self.top_grid_layout.addWidget(self._lbl_pasadas_tool_bar, 1, 3, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_paquetes_tool_bar = Qt.QToolBar(self)

        if None:
            self._lbl_paquetes_formatter = None
        else:
            self._lbl_paquetes_formatter = lambda x: str(x)

        self._lbl_paquetes_tool_bar.addWidget(Qt.QLabel("Paquetes por pasada: "))
        self._lbl_paquetes_label = Qt.QLabel(str(self._lbl_paquetes_formatter(self.lbl_paquetes)))
        self._lbl_paquetes_tool_bar.addWidget(self._lbl_paquetes_label)
        self.top_grid_layout.addWidget(self._lbl_paquetes_tool_bar, 1, 1, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_huella_tool_bar = Qt.QToolBar(self)

        if None:
            self._lbl_huella_formatter = None
        else:
            self._lbl_huella_formatter = lambda x: str(x)

        self._lbl_huella_tool_bar.addWidget(Qt.QLabel("SHA-256: "))
        self._lbl_huella_label = Qt.QLabel(str(self._lbl_huella_formatter(self.lbl_huella)))
        self._lbl_huella_tool_bar.addWidget(self._lbl_huella_label)
        self.top_grid_layout.addWidget(self._lbl_huella_tool_bar, 1, 2, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_archivo_tool_bar = Qt.QToolBar(self)

        if None:
            self._lbl_archivo_formatter = None
        else:
            self._lbl_archivo_formatter = lambda x: str(x)

        self._lbl_archivo_tool_bar.addWidget(Qt.QLabel("Archivo: "))
        self._lbl_archivo_label = Qt.QLabel(str(self._lbl_archivo_formatter(self.lbl_archivo)))
        self._lbl_archivo_tool_bar.addWidget(self._lbl_archivo_label)
        self.top_grid_layout.addWidget(self._lbl_archivo_tool_bar, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.hackrf_tx = None
        dev = 'driver=hackrf'
        stream_args = ''
        tune_args = ['']
        settings = ['']

        self.hackrf_tx = soapy.sink(dev, "fc32", 1, dispositivo,
                                  stream_args, tune_args, settings)
        self.hackrf_tx.set_sample_rate(0, samp_rate)
        self.hackrf_tx.set_bandwidth(0, 0)
        self.hackrf_tx.set_frequency(0, (freq_mhz * 1e6 - f_offset))
        self.hackrf_tx.set_gain(0, 'AMP', amp_tx)
        self.hackrf_tx.set_gain(0, 'VGA', min(max(vga_tx, 0.0), 47.0))
        self.g_senal = qtgui.time_sink_c(
            400, #size
            samp_rate, #samp_rate
            "Señal que entra al HackRF (I y Q, debe quedar dentro de ±1)", #name
            1, #number of inputs
            None # parent
        )
        self.g_senal.set_update_time(0.10)
        self.g_senal.set_y_axis(-1.1, 1.1)

        self.g_senal.set_y_label('Amplitud', "")

        self.g_senal.enable_tags(False)
        self.g_senal.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_senal.enable_autoscale(False)
        self.g_senal.enable_grid(True)
        self.g_senal.enable_axis_labels(True)
        self.g_senal.enable_control_panel(False)
        self.g_senal.enable_stem_plot(False)


        labels = ['I', 'Q', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(2):
            if len(labels[i]) == 0:
                if (i % 2 == 0):
                    self.g_senal.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.g_senal.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.g_senal.set_line_label(i, labels[i])
            self.g_senal.set_line_width(i, widths[i])
            self.g_senal.set_line_color(i, colors[i])
            self.g_senal.set_line_style(i, styles[i])
            self.g_senal.set_line_marker(i, markers[i])
            self.g_senal.set_line_alpha(i, alphas[i])

        self._g_senal_win = sip.wrapinstance(self.g_senal.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._g_senal_win, 2, 2, 1, 2)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.g_espectro = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Espectro que se transmite (centro = frecuencia - 400 kHz)", #name
            1,
            None # parent
        )
        self.g_espectro.set_update_time(0.10)
        self.g_espectro.set_y_axis((-120), 0)
        self.g_espectro.set_y_label("Potencia relativa", 'dB')
        self.g_espectro.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.g_espectro.enable_autoscale(False)
        self.g_espectro.enable_grid(True)
        self.g_espectro.set_fft_average(0.2)
        self.g_espectro.enable_axis_labels(True)
        self.g_espectro.enable_control_panel(False)
        self.g_espectro.set_fft_window_normalized(False)

        self.g_espectro.disable_legend()


        labels = ['TX', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.g_espectro.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_espectro.set_line_label(i, labels[i])
            self.g_espectro.set_line_width(i, widths[i])
            self.g_espectro.set_line_color(i, colors[i])
            self.g_espectro.set_line_alpha(i, alphas[i])

        self._g_espectro_win = sip.wrapinstance(self.g_espectro.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._g_espectro_win, 2, 0, 1, 1)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.g_cascada = qtgui.waterfall_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Cascada (espectro en el tiempo)", #name
            1, #number of inputs
            None # parent
        )
        self.g_cascada.set_update_time(0.10)
        self.g_cascada.enable_grid(False)
        self.g_cascada.enable_axis_labels(True)

        self.g_cascada.disable_legend()


        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.g_cascada.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_cascada.set_line_label(i, labels[i])
            self.g_cascada.set_color_map(i, colors[i])
            self.g_cascada.set_line_alpha(i, alphas[i])

        self.g_cascada.set_intensity_range(-120, 0)

        self._g_cascada_win = sip.wrapinstance(self.g_cascada.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._g_cascada_win, 2, 1, 1, 1)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        def _enviados_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.limite.nitems_written(0)
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_enviados,val))
              except AttributeError:
                self.set_enviados(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (2))
        _enviados_thread = threading.Thread(target=_enviados_probe)
        _enviados_thread.daemon = True
        _enviados_thread.start()
        self.encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self.desplazar = blocks.rotator_cc((2 * math.pi * f_offset / samp_rate), False)
        self.datos_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, N, "packet_len")
        self.datos_fuente = blocks.vector_source_b(datos, True, 1, [])
        self.crc = digital.crc32_bb(False, "packet_len", True)
        self.ajuste_amplitud = blocks.multiply_const_cc(amplitud)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.ajuste_amplitud, 0), (self.g_cascada, 0))
        self.connect((self.ajuste_amplitud, 0), (self.g_espectro, 0))
        self.connect((self.ajuste_amplitud, 0), (self.g_senal, 0))
        self.connect((self.ajuste_amplitud, 0), (self.hackrf_tx, 0))
        self.connect((self.crc, 0), (self.encabezado, 0))
        self.connect((self.crc, 0), (self.trama, 1))
        self.connect((self.datos_fuente, 0), (self.datos_paquetes, 0))
        self.connect((self.datos_paquetes, 0), (self.paquete, 1))
        self.connect((self.desplazar, 0), (self.ajuste_amplitud, 0))
        self.connect((self.encabezado, 0), (self.trama, 0))
        self.connect((self.limite, 0), (self.modulador, 0))
        self.connect((self.modulador, 0), (self.desplazar, 0))
        self.connect((self.paquete, 0), (self.crc, 0))
        self.connect((self.pasada, 0), (self.limite, 0))
        self.connect((self.relleno_fuente, 0), (self.pasada, 0))
        self.connect((self.sec_fuente, 0), (self.sec_paquetes, 0))
        self.connect((self.sec_paquetes, 0), (self.paquete, 0))
        self.connect((self.trama, 0), (self.pasada, 1))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "hackrf_tx_archivo")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_archivo(self):
        return self.archivo

    def set_archivo(self, archivo):
        self.archivo = archivo
        self.set_encontrado(os.path.isfile(self.archivo))
        self.set_contenido(list(open(self.archivo, "rb").read()) if self.encontrado else list(("No se encontro el archivo " + self.archivo).encode()))
        self.set_nombre(os.path.basename(self.archivo) if self.encontrado else "ERROR_archivo_no_encontrado.txt")

    def get_repeticiones(self):
        return self.repeticiones

    def set_repeticiones(self, repeticiones):
        self.repeticiones = repeticiones
        self.set_total_bytes(self.repeticiones * self.bytes_pasada + self.W if self.repeticiones > 0 else 2**62)

    def get_encontrado(self):
        return self.encontrado

    def set_encontrado(self, encontrado):
        self.encontrado = encontrado
        self.set_contenido(list(open(self.archivo, "rb").read()) if self.encontrado else list(("No se encontro el archivo " + self.archivo).encode()))
        self.set_nombre(os.path.basename(self.archivo) if self.encontrado else "ERROR_archivo_no_encontrado.txt")

    def get_contenido(self):
        return self.contenido

    def set_contenido(self, contenido):
        self.contenido = contenido
        self.set_huella(hashlib.sha256(bytes(self.contenido)).hexdigest())
        self.set_n_datos((len(self.contenido) + self.N - 1) // self.N)
        self.set_descripcion(list(b"ARCHIVO|" + nombre.encode()[:40] + ("|%d|%d|%d|%s|" % (len(self.contenido), self.N, self.n_paq, self.huella)).encode()))
        self.set_datos(self.contenido + [0] * (self.n_datos * self.N - len(self.contenido)) + (self.descripcion + [0] * self.N)[:self.N])
        self.set_lbl_archivo("%s (%d bytes)" % (self.nombre, len(self.contenido)))

    def get_N(self):
        return self.N

    def set_N(self, N):
        self.N = N
        self.set_n_datos((len(self.contenido) + self.N - 1) // self.N)
        self.set_descripcion(list(b"ARCHIVO|" + nombre.encode()[:40] + ("|%d|%d|%d|%s|" % (len(self.contenido), self.N, self.n_paq, self.huella)).encode()))
        self.set_datos(self.contenido + [0] * (self.n_datos * self.N - len(self.contenido)) + (self.descripcion + [0] * self.N)[:self.N])
        self.set_bytes_trama(self.N + 18)
        self.datos_paquetes.set_packet_len(self.N)
        self.datos_paquetes.set_packet_len_pmt(self.N)

    def get_n_datos(self):
        return self.n_datos

    def set_n_datos(self, n_datos):
        self.n_datos = n_datos
        self.set_n_paq(self.n_datos + 1)
        self.set_datos(self.contenido + [0] * (self.n_datos * self.N - len(self.contenido)) + (self.descripcion + [0] * self.N)[:self.N])

    def get_n_paq(self):
        return self.n_paq

    def set_n_paq(self, n_paq):
        self.n_paq = n_paq
        self.set_descripcion(list(b"ARCHIVO|" + nombre.encode()[:40] + ("|%d|%d|%d|%s|" % (len(self.contenido), self.N, self.n_paq, self.huella)).encode()))
        self.set_secuencia([b for i in range(self.n_paq) for b in ((i // 256) % 256, i % 256)])
        self.set_bytes_pasada(self.W + self.n_paq * self.bytes_trama)
        self.set_lbl_paquetes("%d (%.2f s cada pasada)" % (self.n_paq, self.duracion_pasada))

    def get_bytes_trama(self):
        return self.bytes_trama

    def set_bytes_trama(self, bytes_trama):
        self.bytes_trama = bytes_trama
        self.set_bytes_pasada(self.W + self.n_paq * self.bytes_trama)

    def get_W(self):
        return self.W

    def set_W(self, W):
        self.W = W
        self.set_relleno(list(random.Random(1).randbytes(self.W)))
        self.set_bytes_pasada(self.W + self.n_paq * self.bytes_trama)
        self.set_total_bytes(self.repeticiones * self.bytes_pasada + self.W if self.repeticiones > 0 else 2**62)
        self.set_lbl_pasadas((min(self.enviados, self.total_bytes - self.W) / self.bytes_pasada))

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_duracion_pasada(self.bytes_pasada * 8 / 2 / (self.samp_rate / self.sps))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_duracion_pasada(self.bytes_pasada * 8 / 2 / (self.samp_rate / self.sps))
        self.desplazar.set_phase_inc((2 * math.pi * self.f_offset / self.samp_rate))
        self.hackrf_tx.set_sample_rate(0, self.samp_rate)
        self.g_espectro.set_frequency_range(0, self.samp_rate)
        self.g_cascada.set_frequency_range(0, self.samp_rate)
        self.g_senal.set_samp_rate(self.samp_rate)

    def get_nombre(self):
        return self.nombre

    def set_nombre(self, nombre):
        self.nombre = nombre
        self.set_lbl_archivo("%s (%d bytes)" % (self.nombre, len(self.contenido)))

    def get_huella(self):
        return self.huella

    def set_huella(self, huella):
        self.huella = huella
        self.set_descripcion(list(b"ARCHIVO|" + nombre.encode()[:40] + ("|%d|%d|%d|%s|" % (len(self.contenido), self.N, self.n_paq, self.huella)).encode()))
        self.set_lbl_huella(self.huella[:16] + "...")

    def get_bytes_pasada(self):
        return self.bytes_pasada

    def set_bytes_pasada(self, bytes_pasada):
        self.bytes_pasada = bytes_pasada
        self.set_total_bytes(self.repeticiones * self.bytes_pasada + self.W if self.repeticiones > 0 else 2**62)
        self.set_duracion_pasada(self.bytes_pasada * 8 / 2 / (self.samp_rate / self.sps))
        self.set_lbl_pasadas((min(self.enviados, self.total_bytes - self.W) / self.bytes_pasada))

    def get_total_bytes(self):
        return self.total_bytes

    def set_total_bytes(self, total_bytes):
        self.total_bytes = total_bytes
        self.set_lbl_pasadas((min(self.enviados, self.total_bytes - self.W) / self.bytes_pasada))
        self.limite.set_length(self.total_bytes)

    def get_enviados(self):
        return self.enviados

    def set_enviados(self, enviados):
        self.enviados = enviados
        self.set_lbl_pasadas((min(self.enviados, self.total_bytes - self.W) / self.bytes_pasada))

    def get_duracion_pasada(self):
        return self.duracion_pasada

    def set_duracion_pasada(self, duracion_pasada):
        self.duracion_pasada = duracion_pasada
        self.set_lbl_paquetes("%d (%.2f s cada pasada)" % (self.n_paq, self.duracion_pasada))

    def get_descripcion(self):
        return self.descripcion

    def set_descripcion(self, descripcion):
        self.descripcion = descripcion
        self.set_datos(self.contenido + [0] * (self.n_datos * self.N - len(self.contenido)) + (self.descripcion + [0] * self.N)[:self.N])

    def get_vga_tx(self):
        return self.vga_tx

    def set_vga_tx(self, vga_tx):
        self.vga_tx = vga_tx
        self.hackrf_tx.set_gain(0, 'VGA', min(max(self.vga_tx, 0.0), 47.0))

    def get_secuencia(self):
        return self.secuencia

    def set_secuencia(self, secuencia):
        self.secuencia = secuencia
        self.sec_fuente.set_data(self.secuencia, [])

    def get_relleno(self):
        return self.relleno

    def set_relleno(self, relleno):
        self.relleno = relleno
        self.relleno_fuente.set_data(self.relleno, [])

    def get_qpsk(self):
        return self.qpsk

    def set_qpsk(self, qpsk):
        self.qpsk = qpsk

    def get_lbl_pasadas(self):
        return self.lbl_pasadas

    def set_lbl_pasadas(self, lbl_pasadas):
        self.lbl_pasadas = lbl_pasadas
        Qt.QMetaObject.invokeMethod(self._lbl_pasadas_label, "setText", Qt.Q_ARG("QString", str(self._lbl_pasadas_formatter(self.lbl_pasadas))))

    def get_lbl_paquetes(self):
        return self.lbl_paquetes

    def set_lbl_paquetes(self, lbl_paquetes):
        self.lbl_paquetes = lbl_paquetes
        Qt.QMetaObject.invokeMethod(self._lbl_paquetes_label, "setText", Qt.Q_ARG("QString", str(self._lbl_paquetes_formatter(self.lbl_paquetes))))

    def get_lbl_huella(self):
        return self.lbl_huella

    def set_lbl_huella(self, lbl_huella):
        self.lbl_huella = lbl_huella
        Qt.QMetaObject.invokeMethod(self._lbl_huella_label, "setText", Qt.Q_ARG("QString", str(self._lbl_huella_formatter(self.lbl_huella))))

    def get_lbl_archivo(self):
        return self.lbl_archivo

    def set_lbl_archivo(self, lbl_archivo):
        self.lbl_archivo = lbl_archivo
        Qt.QMetaObject.invokeMethod(self._lbl_archivo_label, "setText", Qt.Q_ARG("QString", str(self._lbl_archivo_formatter(self.lbl_archivo))))

    def get_freq_mhz(self):
        return self.freq_mhz

    def set_freq_mhz(self, freq_mhz):
        self.freq_mhz = freq_mhz
        Qt.QMetaObject.invokeMethod(self._freq_mhz_line_edit, "setText", Qt.Q_ARG("QString", eng_notation.num_to_str(self.freq_mhz)))
        self.hackrf_tx.set_frequency(0, (self.freq_mhz * 1e6 - self.f_offset))

    def get_formato_trama(self):
        return self.formato_trama

    def set_formato_trama(self, formato_trama):
        self.formato_trama = formato_trama
        self.encabezado.set_header_format(self.formato_trama)

    def get_f_offset(self):
        return self.f_offset

    def set_f_offset(self, f_offset):
        self.f_offset = f_offset
        self.desplazar.set_phase_inc((2 * math.pi * self.f_offset / self.samp_rate))
        self.hackrf_tx.set_frequency(0, (self.freq_mhz * 1e6 - self.f_offset))

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw

    def get_dispositivo(self):
        return self.dispositivo

    def set_dispositivo(self, dispositivo):
        self.dispositivo = dispositivo

    def get_datos(self):
        return self.datos

    def set_datos(self, datos):
        self.datos = datos
        self.datos_fuente.set_data(self.datos, [])

    def get_amplitud(self):
        return self.amplitud

    def set_amplitud(self, amplitud):
        self.amplitud = amplitud
        self.ajuste_amplitud.set_k(self.amplitud)

    def get_amp_tx(self):
        return self.amp_tx

    def set_amp_tx(self, amp_tx):
        self.amp_tx = amp_tx
        self._amp_tx_callback(self.amp_tx)
        self.hackrf_tx.set_gain(0, 'AMP', self.amp_tx)



def argument_parser():
    description = 'Transmite un archivo en paquetes numerados (CRC-32, preámbulo y longitud) con 4-QAM diferencial por un HackRF; solo bloques estándar de GNU Radio'
    parser = ArgumentParser(description=description)
    parser.add_argument(
        "--archivo", dest="archivo", type=str, default='archivo_a_enviar.txt',
        help="Set Archivo a transmitir [default=%(default)r]")
    parser.add_argument(
        "--repeticiones", dest="repeticiones", type=intx, default=3,
        help="Set Veces que se envía el archivo (0 = sin fin) [default=%(default)r]")
    return parser


def main(top_block_cls=hackrf_tx_archivo, options=None):
    if options is None:
        options = argument_parser().parse_args()

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(archivo=options.archivo, repeticiones=options.repeticiones)

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
