#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Enlace half-duplex 4-QAM (TDD) con tramas y BER (bloques estándar)
# Author: Juan Gerez
# Description: Dos nodos que se turnan un canal compartido (TDD) con tramas (preámbulo + longitud + CRC-32), 4-QAM diferencial y medición de BER; solo bloques estándar de GNU Radio
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio import eng_notation
from gnuradio import fec
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
import math, cmath
import sip
import threading
import time



class halfduplex_4qam(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Enlace half-duplex 4-QAM (TDD) con tramas y BER (bloques estándar)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Enlace half-duplex 4-QAM (TDD) con tramas y BER (bloques estándar)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "halfduplex_4qam")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.ebn0_db = ebn0_db = 10
        self.p_qpsk = p_qpsk = 0.5 * math.erfc(math.sqrt(10**(ebn0_db / 10)))
        self.mensaje_B = mensaje_B = "Hola, soy el nodo B. Respondo en la otra ranura: nunca transmitimos los dos al mismo tiempo!!"
        self.mensaje_A = mensaje_A = "Hola, soy el nodo A. Este mensaje viaja por el canal compartido en mi ranura de tiempo (TDD)."
        self.sps = sps = 4
        self.payload_B = payload_B = list(mensaje_B.encode())
        self.payload_A = payload_A = list(mensaje_A.encode())
        self.ber_teo = ber_teo = 2 * p_qpsk * (1 - p_qpsk)
        self.ber_B_log = ber_B_log = 0
        self.ber_A_log = ber_A_log = 0
        self.ventana = ventana = 1000000
        self.umbral = umbral = 12
        self.sync_bw = sync_bw = 0.01
        self.samp_rate = samp_rate = 500000
        self.ruido = ruido = math.sqrt(sps / (2 * 10**(ebn0_db / 10)))
        self.ranura = ranura = 2048
        self.qpsk = qpsk = digital.constellation_rect([-0.707-0.707j, 0.707-0.707j, +0.707+0.707j, -0.707+0.707j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.lbl_teo = lbl_teo = ber_teo
        self.lbl_ratio = lbl_ratio = (10**ber_A_log / ber_teo, 10**ber_B_log / ber_teo)
        self.lbl_B = lbl_B = (10**ber_B_log)
        self.lbl_A = lbl_A = (10**ber_A_log)
        self.guarda = guarda = 256
        self.formato_trama = formato_trama = digital.header_format_default(digital.packet_utils.default_access_code,0, 1)
        self.fase_deg = fase_deg = 0
        self.excess_bw = excess_bw = 0.35
        self.costas_bw = costas_bw = 0.005
        self.cfo_hz = cfo_hz = 0
        self.L_B = L_B = len(payload_B)
        self.L_A = L_A = len(payload_A)

        ##################################################
        # Blocks
        ##################################################

        self._sync_bw_range = qtgui.Range(0.001, 0.1, 0.001, 0.01, 100)
        self._sync_bw_win = qtgui.RangeWidget(self._sync_bw_range, self.set_sync_bw, "BW sinc. de símbolo", "counter", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._sync_bw_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.rxB_sonda_ber = blocks.probe_signal_f()
        self.rxA_sonda_ber = blocks.probe_signal_f()
        self.pestanas = Qt.QTabWidget()
        self.pestanas_widget_0 = Qt.QWidget()
        self.pestanas_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_0)
        self.pestanas_grid_layout_0 = Qt.QGridLayout()
        self.pestanas_layout_0.addLayout(self.pestanas_grid_layout_0)
        self.pestanas.addTab(self.pestanas_widget_0, '1. Canal compartido (TDD)')
        self.pestanas_widget_1 = Qt.QWidget()
        self.pestanas_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_1)
        self.pestanas_grid_layout_1 = Qt.QGridLayout()
        self.pestanas_layout_1.addLayout(self.pestanas_grid_layout_1)
        self.pestanas.addTab(self.pestanas_widget_1, '2. Nodo A recibe (lo que transmite B)')
        self.pestanas_widget_2 = Qt.QWidget()
        self.pestanas_layout_2 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_2)
        self.pestanas_grid_layout_2 = Qt.QGridLayout()
        self.pestanas_layout_2.addLayout(self.pestanas_grid_layout_2)
        self.pestanas.addTab(self.pestanas_widget_2, '3. Nodo B recibe (lo que transmite A)')
        self.top_grid_layout.addWidget(self.pestanas, 2, 0, 1, 6)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._costas_bw_range = qtgui.Range(0.001, 0.1, 0.001, 0.005, 100)
        self._costas_bw_win = qtgui.RangeWidget(self._costas_bw_range, self.set_costas_bw, "BW lazo de Costas", "counter", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._costas_bw_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._cfo_hz_range = qtgui.Range(-1000, 1000, 10, 0, 150)
        self._cfo_hz_win = qtgui.RangeWidget(self._cfo_hz_range, self.set_cfo_hz, "Desvío entre osciladores A-B [Hz]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._cfo_hz_win, 0, 4, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.txB_trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.txB_modulador = digital.generic_mod(
            constellation=qpsk,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=excess_bw,
            verbose=False,
            log=False,
            truncate=False)
        self.txB_fuente = blocks.vector_source_b(payload_B, True, 1, [])
        self.txB_encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self.txB_crc = digital.crc32_bb(False, "packet_len", True)
        self.txB_a_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, L_B, "packet_len")
        self.txA_trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.txA_modulador = digital.generic_mod(
            constellation=qpsk,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=excess_bw,
            verbose=False,
            log=False,
            truncate=False)
        self.txA_fuente = blocks.vector_source_b(payload_A, True, 1, [])
        self.txA_encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self.txA_crc = digital.crc32_bb(False, "packet_len", True)
        self.txA_a_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, L_A, "packet_len")
        self.turnos = blocks.stream_mux(gr.sizeof_gr_complex*1, [ranura, guarda, ranura, guarda])
        self.turno_B = blocks.vector_source_f([0.0] * (ranura + guarda) + [1.8] * ranura + [0.0] * guarda, True, 1, [])
        self.turno_A = blocks.vector_source_f([1.8] * ranura + [0.0] * (guarda + ranura + guarda), True, 1, [])
        self.suma_ruido = blocks.add_vcc(1)
        self.silencio_3 = blocks.null_source(gr.sizeof_gr_complex*1)
        self.silencio_1 = blocks.null_source(gr.sizeof_gr_complex*1)
        self.rxB_una_de_cien = blocks.keep_m_in_n(gr.sizeof_char, L_A, (100*L_A), 0)
        self.rxB_submuestreo = blocks.keep_one_in_n(gr.sizeof_float*1, 1000)
        self.rxB_sinc_simbolo = digital.symbol_sync_cc(
            digital.TED_SIGNAL_TIMES_SLOPE_ML,
            sps,
            sync_bw,
            1.0,
            1.0,
            1.5,
            1,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.rxB_sinc_null_3 = blocks.null_sink(gr.sizeof_float*1)
        self.rxB_sinc_null_2 = blocks.null_sink(gr.sizeof_float*1)
        self.rxB_sinc_null_1 = blocks.null_sink(gr.sizeof_float*1)
        self.rxB_rx_bytes = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rxB_rx_bit_f = blocks.char_to_float(1, 1)
        self.rxB_ref_trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.rxB_ref_saltar_preambulo = blocks.skiphead(gr.sizeof_char*1, 64)
        self.rxB_ref_fuente = blocks.vector_source_b(payload_A, True, 1, [])
        self.rxB_ref_encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self.rxB_ref_desplazar = blocks.add_const_ff(1.5)
        self.rxB_ref_crc = digital.crc32_bb(False, "packet_len", True)
        self.rxB_ref_bytes = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rxB_ref_bits = blocks.unpack_k_bits_bb(8)
        self.rxB_ref_bit_f = blocks.char_to_float(1, 1)
        self.rxB_ref_a_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, L_A, "packet_len")
        self.rxB_payload_f = blocks.char_to_float(1, 1)
        self.rxB_ojo_re = blocks.complex_to_real(1)
        self.rxB_ojo_interp = filter.rational_resampler_ccc(
                interpolation=4,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.rxB_medidor_ber = fec.ber_bf(False, 100, -7.0)
        self.rxB_marca_preambulo = digital.correlate_access_code_tag_bb(digital.packet_utils.default_access_code, umbral, "inicio_trama")
        self.rxB_mapa_gray = digital.map_bb([0, 1, 3, 2])
        self.rxB_log_teo = analog.sig_source_f((samp_rate/sps*2/1000), analog.GR_CONST_WAVE, 0, math.log10(ber_teo), 0, 0)
        self.rxB_log_ber = blocks.nlog10_ff(1, 1, 0)
        self.rxB_g_payload = qtgui.time_sink_f(
            (2 * 8 * (L_A + 4)), #size
            samp_rate/sps*2, #samp_rate
            "Payload del detector de tramas", #name
            1, #number of inputs
            None # parent
        )
        self.rxB_g_payload.set_update_time(0.10)
        self.rxB_g_payload.set_y_axis(-0.5, 1.5)

        self.rxB_g_payload.set_y_label('Bit', "")

        self.rxB_g_payload.enable_tags(True)
        self.rxB_g_payload.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxB_g_payload.enable_autoscale(False)
        self.rxB_g_payload.enable_grid(True)
        self.rxB_g_payload.enable_axis_labels(True)
        self.rxB_g_payload.enable_control_panel(False)
        self.rxB_g_payload.enable_stem_plot(False)

        self.rxB_g_payload.disable_legend()

        labels = ['Payload + CRC', '', '', '', '',
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


        for i in range(1):
            if len(labels[i]) == 0:
                self.rxB_g_payload.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxB_g_payload.set_line_label(i, labels[i])
            self.rxB_g_payload.set_line_width(i, widths[i])
            self.rxB_g_payload.set_line_color(i, colors[i])
            self.rxB_g_payload.set_line_style(i, styles[i])
            self.rxB_g_payload.set_line_marker(i, markers[i])
            self.rxB_g_payload.set_line_alpha(i, alphas[i])

        self._rxB_g_payload_win = sip.wrapinstance(self.rxB_g_payload.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._rxB_g_payload_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.rxB_g_ojo = qtgui.eye_sink_f(
            2048, #size
            4*samp_rate, #samp_rate
            1, #number of inputs
            None
        )
        self.rxB_g_ojo.set_update_time(0.10)
        self.rxB_g_ojo.set_samp_per_symbol((4*sps))
        self.rxB_g_ojo.set_y_axis(-1.5, 1.5)

        self.rxB_g_ojo.set_y_label("Amplitud", "")

        self.rxB_g_ojo.enable_tags(False)
        self.rxB_g_ojo.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxB_g_ojo.enable_autoscale(False)
        self.rxB_g_ojo.enable_grid(True)
        self.rxB_g_ojo.enable_axis_labels(True)
        self.rxB_g_ojo.enable_control_panel(False)


        labels = ['Ojo de la componente I (antes de Costas)', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'blue', 'blue', 'blue', 'blue',
            'blue', 'blue', 'blue', 'blue', 'blue']
        alphas = [0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.rxB_g_ojo.set_line_label(i, "Eye[Data {0}]".format(i))
            else:
                self.rxB_g_ojo.set_line_label(i, labels[i])
            self.rxB_g_ojo.set_line_width(i, widths[i])
            self.rxB_g_ojo.set_line_color(i, colors[i])
            self.rxB_g_ojo.set_line_style(i, styles[i])
            self.rxB_g_ojo.set_line_marker(i, markers[i])
            self.rxB_g_ojo.set_line_alpha(i, alphas[i])

        self._rxB_g_ojo_win = sip.wrapinstance(self.rxB_g_ojo.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._rxB_g_ojo_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.rxB_g_frec = qtgui.time_sink_f(
            2000, #size
            samp_rate/sps, #samp_rate
            "Frecuencia de Costas vs CFO [Hz]", #name
            2, #number of inputs
            None # parent
        )
        self.rxB_g_frec.set_update_time(0.10)
        self.rxB_g_frec.set_y_axis(-1100, 1100)

        self.rxB_g_frec.set_y_label('Hz', "")

        self.rxB_g_frec.enable_tags(False)
        self.rxB_g_frec.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxB_g_frec.enable_autoscale(False)
        self.rxB_g_frec.enable_grid(True)
        self.rxB_g_frec.enable_axis_labels(True)
        self.rxB_g_frec.enable_control_panel(False)
        self.rxB_g_frec.enable_stem_plot(False)


        labels = ['Costas', 'CFO (+Δf)', '', '', '',
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
                self.rxB_g_frec.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxB_g_frec.set_line_label(i, labels[i])
            self.rxB_g_frec.set_line_width(i, widths[i])
            self.rxB_g_frec.set_line_color(i, colors[i])
            self.rxB_g_frec.set_line_style(i, styles[i])
            self.rxB_g_frec.set_line_marker(i, markers[i])
            self.rxB_g_frec.set_line_alpha(i, alphas[i])

        self._rxB_g_frec_win = sip.wrapinstance(self.rxB_g_frec.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._rxB_g_frec_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.rxB_g_const = qtgui.const_sink_c(
            1024, #size
            "Constelación antes y después de Costas", #name
            2, #number of inputs
            None # parent
        )
        self.rxB_g_const.set_update_time(0.10)
        self.rxB_g_const.set_y_axis((-1.5), 1.5)
        self.rxB_g_const.set_x_axis((-1.5), 1.5)
        self.rxB_g_const.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.rxB_g_const.enable_autoscale(False)
        self.rxB_g_const.enable_grid(True)
        self.rxB_g_const.enable_axis_labels(True)


        labels = ['Antes', 'Después', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [0.6, 0.6, 0.6, 0.6, 0.6,
            0.6, 0.6, 0.6, 0.6, 0.6]

        for i in range(2):
            if len(labels[i]) == 0:
                self.rxB_g_const.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxB_g_const.set_line_label(i, labels[i])
            self.rxB_g_const.set_line_width(i, widths[i])
            self.rxB_g_const.set_line_color(i, colors[i])
            self.rxB_g_const.set_line_style(i, styles[i])
            self.rxB_g_const.set_line_marker(i, markers[i])
            self.rxB_g_const.set_line_alpha(i, alphas[i])

        self._rxB_g_const_win = sip.wrapinstance(self.rxB_g_const.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._rxB_g_const_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.rxB_g_bits = qtgui.time_sink_f(
            200, #size
            samp_rate/sps*2, #samp_rate
            "Bits RX vs TX (+1,5) y errores", #name
            3, #number of inputs
            None # parent
        )
        self.rxB_g_bits.set_update_time(0.10)
        self.rxB_g_bits.set_y_axis(-1, 4)

        self.rxB_g_bits.set_y_label('Bit', "")

        self.rxB_g_bits.enable_tags(False)
        self.rxB_g_bits.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxB_g_bits.enable_autoscale(False)
        self.rxB_g_bits.enable_grid(True)
        self.rxB_g_bits.enable_axis_labels(True)
        self.rxB_g_bits.enable_control_panel(False)
        self.rxB_g_bits.enable_stem_plot(False)


        labels = ['RX', 'TX (+1,5)', 'Errores', '', '',
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


        for i in range(3):
            if len(labels[i]) == 0:
                self.rxB_g_bits.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxB_g_bits.set_line_label(i, labels[i])
            self.rxB_g_bits.set_line_width(i, widths[i])
            self.rxB_g_bits.set_line_color(i, colors[i])
            self.rxB_g_bits.set_line_style(i, styles[i])
            self.rxB_g_bits.set_line_marker(i, markers[i])
            self.rxB_g_bits.set_line_alpha(i, alphas[i])

        self._rxB_g_bits_win = sip.wrapinstance(self.rxB_g_bits.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._rxB_g_bits_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.rxB_g_ber = qtgui.time_sink_f(
            500, #size
            samp_rate/sps*2/1000, #samp_rate
            "log10(BER): medido vs teórico", #name
            2, #number of inputs
            None # parent
        )
        self.rxB_g_ber.set_update_time(0.10)
        self.rxB_g_ber.set_y_axis(-6, 0)

        self.rxB_g_ber.set_y_label('log10(BER)', "")

        self.rxB_g_ber.enable_tags(False)
        self.rxB_g_ber.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxB_g_ber.enable_autoscale(False)
        self.rxB_g_ber.enable_grid(True)
        self.rxB_g_ber.enable_axis_labels(True)
        self.rxB_g_ber.enable_control_panel(False)
        self.rxB_g_ber.enable_stem_plot(False)


        labels = ['Medido (último Mbit)', 'Teórico', '', '', '',
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
                self.rxB_g_ber.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxB_g_ber.set_line_label(i, labels[i])
            self.rxB_g_ber.set_line_width(i, widths[i])
            self.rxB_g_ber.set_line_color(i, colors[i])
            self.rxB_g_ber.set_line_style(i, styles[i])
            self.rxB_g_ber.set_line_marker(i, markers[i])
            self.rxB_g_ber.set_line_alpha(i, alphas[i])

        self._rxB_g_ber_win = sip.wrapinstance(self.rxB_g_ber.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._rxB_g_ber_win, 1, 2, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.rxB_frec_hz = blocks.multiply_const_ff((samp_rate / sps / (2 * math.pi)))
        self.rxB_filtro_adaptado = filter.fft_filter_ccc(1, firdes.root_raised_cosine(1, samp_rate, (samp_rate/sps), excess_bw, (11*sps)), 1)
        self.rxB_errores = blocks.char_to_float(1, 1)
        self.rxB_detector_trama = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code,
          umbral, "packet_len")
        self.rxB_detector_trama.set_min_output_buffer(600000)
        self.rxB_decisor = digital.constellation_decoder_cb(qpsk)
        self.rxB_dec_diferencial = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.rxB_crc = digital.crc32_bb(True, "packet_len", True)
        self.rxB_crc.set_min_output_buffer(70000)
        self.rxB_costas = digital.costas_loop_cc(costas_bw, 4, False)
        self.rxB_comparar = blocks.xor_bb()
        self.rxB_cfo_esperado = analog.sig_source_f((samp_rate/sps), analog.GR_CONST_WAVE, 0, cfo_hz, 0, 0)
        self.rxB_ber_ventana = blocks.moving_average_ff(ventana, (1.0/ventana), 4000, 1)
        self.rxB_archivo = blocks.file_sink(gr.sizeof_char*1, "mensajes_recibidos_B.txt", False)
        self.rxB_archivo.set_unbuffered(True)
        self.rxB_alinear = blocks.tagged_stream_align(gr.sizeof_char*1, "inicio_trama")
        self.rxB_a_bytes = blocks.repack_bits_bb(1, 8, "packet_len", True, gr.GR_MSB_FIRST)
        self.rxB_a_bytes.set_min_output_buffer(70000)
        self.rxB_a_bits = blocks.unpack_k_bits_bb(2)
        self.rxA_una_de_cien = blocks.keep_m_in_n(gr.sizeof_char, L_B, (100*L_B), 0)
        self.rxA_submuestreo = blocks.keep_one_in_n(gr.sizeof_float*1, 1000)
        self.rxA_sinc_simbolo = digital.symbol_sync_cc(
            digital.TED_SIGNAL_TIMES_SLOPE_ML,
            sps,
            sync_bw,
            1.0,
            1.0,
            1.5,
            1,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.rxA_sinc_null_3 = blocks.null_sink(gr.sizeof_float*1)
        self.rxA_sinc_null_2 = blocks.null_sink(gr.sizeof_float*1)
        self.rxA_sinc_null_1 = blocks.null_sink(gr.sizeof_float*1)
        self.rxA_rx_bytes = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rxA_rx_bit_f = blocks.char_to_float(1, 1)
        self.rxA_ref_trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.rxA_ref_saltar_preambulo = blocks.skiphead(gr.sizeof_char*1, 64)
        self.rxA_ref_fuente = blocks.vector_source_b(payload_B, True, 1, [])
        self.rxA_ref_encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self.rxA_ref_desplazar = blocks.add_const_ff(1.5)
        self.rxA_ref_crc = digital.crc32_bb(False, "packet_len", True)
        self.rxA_ref_bytes = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rxA_ref_bits = blocks.unpack_k_bits_bb(8)
        self.rxA_ref_bit_f = blocks.char_to_float(1, 1)
        self.rxA_ref_a_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, L_B, "packet_len")
        self.rxA_payload_f = blocks.char_to_float(1, 1)
        self.rxA_ojo_re = blocks.complex_to_real(1)
        self.rxA_ojo_interp = filter.rational_resampler_ccc(
                interpolation=4,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.rxA_medidor_ber = fec.ber_bf(False, 100, -7.0)
        self.rxA_marca_preambulo = digital.correlate_access_code_tag_bb(digital.packet_utils.default_access_code, umbral, "inicio_trama")
        self.rxA_mapa_gray = digital.map_bb([0, 1, 3, 2])
        self.rxA_log_teo = analog.sig_source_f((samp_rate/sps*2/1000), analog.GR_CONST_WAVE, 0, math.log10(ber_teo), 0, 0)
        self.rxA_log_ber = blocks.nlog10_ff(1, 1, 0)
        self.rxA_g_payload = qtgui.time_sink_f(
            (2 * 8 * (L_B + 4)), #size
            samp_rate/sps*2, #samp_rate
            "Payload del detector de tramas", #name
            1, #number of inputs
            None # parent
        )
        self.rxA_g_payload.set_update_time(0.10)
        self.rxA_g_payload.set_y_axis(-0.5, 1.5)

        self.rxA_g_payload.set_y_label('Bit', "")

        self.rxA_g_payload.enable_tags(True)
        self.rxA_g_payload.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxA_g_payload.enable_autoscale(False)
        self.rxA_g_payload.enable_grid(True)
        self.rxA_g_payload.enable_axis_labels(True)
        self.rxA_g_payload.enable_control_panel(False)
        self.rxA_g_payload.enable_stem_plot(False)

        self.rxA_g_payload.disable_legend()

        labels = ['Payload + CRC', '', '', '', '',
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


        for i in range(1):
            if len(labels[i]) == 0:
                self.rxA_g_payload.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxA_g_payload.set_line_label(i, labels[i])
            self.rxA_g_payload.set_line_width(i, widths[i])
            self.rxA_g_payload.set_line_color(i, colors[i])
            self.rxA_g_payload.set_line_style(i, styles[i])
            self.rxA_g_payload.set_line_marker(i, markers[i])
            self.rxA_g_payload.set_line_alpha(i, alphas[i])

        self._rxA_g_payload_win = sip.wrapinstance(self.rxA_g_payload.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._rxA_g_payload_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.rxA_g_ojo = qtgui.eye_sink_f(
            2048, #size
            4*samp_rate, #samp_rate
            1, #number of inputs
            None
        )
        self.rxA_g_ojo.set_update_time(0.10)
        self.rxA_g_ojo.set_samp_per_symbol((4*sps))
        self.rxA_g_ojo.set_y_axis(-1.5, 1.5)

        self.rxA_g_ojo.set_y_label("Amplitud", "")

        self.rxA_g_ojo.enable_tags(False)
        self.rxA_g_ojo.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxA_g_ojo.enable_autoscale(False)
        self.rxA_g_ojo.enable_grid(True)
        self.rxA_g_ojo.enable_axis_labels(True)
        self.rxA_g_ojo.enable_control_panel(False)


        labels = ['Ojo de la componente I (antes de Costas)', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'blue', 'blue', 'blue', 'blue',
            'blue', 'blue', 'blue', 'blue', 'blue']
        alphas = [0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.rxA_g_ojo.set_line_label(i, "Eye[Data {0}]".format(i))
            else:
                self.rxA_g_ojo.set_line_label(i, labels[i])
            self.rxA_g_ojo.set_line_width(i, widths[i])
            self.rxA_g_ojo.set_line_color(i, colors[i])
            self.rxA_g_ojo.set_line_style(i, styles[i])
            self.rxA_g_ojo.set_line_marker(i, markers[i])
            self.rxA_g_ojo.set_line_alpha(i, alphas[i])

        self._rxA_g_ojo_win = sip.wrapinstance(self.rxA_g_ojo.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._rxA_g_ojo_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.rxA_g_frec = qtgui.time_sink_f(
            2000, #size
            samp_rate/sps, #samp_rate
            "Frecuencia de Costas vs CFO [Hz]", #name
            2, #number of inputs
            None # parent
        )
        self.rxA_g_frec.set_update_time(0.10)
        self.rxA_g_frec.set_y_axis(-1100, 1100)

        self.rxA_g_frec.set_y_label('Hz', "")

        self.rxA_g_frec.enable_tags(False)
        self.rxA_g_frec.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxA_g_frec.enable_autoscale(False)
        self.rxA_g_frec.enable_grid(True)
        self.rxA_g_frec.enable_axis_labels(True)
        self.rxA_g_frec.enable_control_panel(False)
        self.rxA_g_frec.enable_stem_plot(False)


        labels = ['Costas', 'CFO (-Δf)', '', '', '',
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
                self.rxA_g_frec.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxA_g_frec.set_line_label(i, labels[i])
            self.rxA_g_frec.set_line_width(i, widths[i])
            self.rxA_g_frec.set_line_color(i, colors[i])
            self.rxA_g_frec.set_line_style(i, styles[i])
            self.rxA_g_frec.set_line_marker(i, markers[i])
            self.rxA_g_frec.set_line_alpha(i, alphas[i])

        self._rxA_g_frec_win = sip.wrapinstance(self.rxA_g_frec.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._rxA_g_frec_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.rxA_g_const = qtgui.const_sink_c(
            1024, #size
            "Constelación antes y después de Costas", #name
            2, #number of inputs
            None # parent
        )
        self.rxA_g_const.set_update_time(0.10)
        self.rxA_g_const.set_y_axis((-1.5), 1.5)
        self.rxA_g_const.set_x_axis((-1.5), 1.5)
        self.rxA_g_const.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.rxA_g_const.enable_autoscale(False)
        self.rxA_g_const.enable_grid(True)
        self.rxA_g_const.enable_axis_labels(True)


        labels = ['Antes', 'Después', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [0.6, 0.6, 0.6, 0.6, 0.6,
            0.6, 0.6, 0.6, 0.6, 0.6]

        for i in range(2):
            if len(labels[i]) == 0:
                self.rxA_g_const.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxA_g_const.set_line_label(i, labels[i])
            self.rxA_g_const.set_line_width(i, widths[i])
            self.rxA_g_const.set_line_color(i, colors[i])
            self.rxA_g_const.set_line_style(i, styles[i])
            self.rxA_g_const.set_line_marker(i, markers[i])
            self.rxA_g_const.set_line_alpha(i, alphas[i])

        self._rxA_g_const_win = sip.wrapinstance(self.rxA_g_const.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._rxA_g_const_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.rxA_g_bits = qtgui.time_sink_f(
            200, #size
            samp_rate/sps*2, #samp_rate
            "Bits RX vs TX (+1,5) y errores", #name
            3, #number of inputs
            None # parent
        )
        self.rxA_g_bits.set_update_time(0.10)
        self.rxA_g_bits.set_y_axis(-1, 4)

        self.rxA_g_bits.set_y_label('Bit', "")

        self.rxA_g_bits.enable_tags(False)
        self.rxA_g_bits.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxA_g_bits.enable_autoscale(False)
        self.rxA_g_bits.enable_grid(True)
        self.rxA_g_bits.enable_axis_labels(True)
        self.rxA_g_bits.enable_control_panel(False)
        self.rxA_g_bits.enable_stem_plot(False)


        labels = ['RX', 'TX (+1,5)', 'Errores', '', '',
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


        for i in range(3):
            if len(labels[i]) == 0:
                self.rxA_g_bits.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxA_g_bits.set_line_label(i, labels[i])
            self.rxA_g_bits.set_line_width(i, widths[i])
            self.rxA_g_bits.set_line_color(i, colors[i])
            self.rxA_g_bits.set_line_style(i, styles[i])
            self.rxA_g_bits.set_line_marker(i, markers[i])
            self.rxA_g_bits.set_line_alpha(i, alphas[i])

        self._rxA_g_bits_win = sip.wrapinstance(self.rxA_g_bits.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._rxA_g_bits_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.rxA_g_ber = qtgui.time_sink_f(
            500, #size
            samp_rate/sps*2/1000, #samp_rate
            "log10(BER): medido vs teórico", #name
            2, #number of inputs
            None # parent
        )
        self.rxA_g_ber.set_update_time(0.10)
        self.rxA_g_ber.set_y_axis(-6, 0)

        self.rxA_g_ber.set_y_label('log10(BER)', "")

        self.rxA_g_ber.enable_tags(False)
        self.rxA_g_ber.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.rxA_g_ber.enable_autoscale(False)
        self.rxA_g_ber.enable_grid(True)
        self.rxA_g_ber.enable_axis_labels(True)
        self.rxA_g_ber.enable_control_panel(False)
        self.rxA_g_ber.enable_stem_plot(False)


        labels = ['Medido (último Mbit)', 'Teórico', '', '', '',
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
                self.rxA_g_ber.set_line_label(i, "Data {0}".format(i))
            else:
                self.rxA_g_ber.set_line_label(i, labels[i])
            self.rxA_g_ber.set_line_width(i, widths[i])
            self.rxA_g_ber.set_line_color(i, colors[i])
            self.rxA_g_ber.set_line_style(i, styles[i])
            self.rxA_g_ber.set_line_marker(i, markers[i])
            self.rxA_g_ber.set_line_alpha(i, alphas[i])

        self._rxA_g_ber_win = sip.wrapinstance(self.rxA_g_ber.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._rxA_g_ber_win, 1, 2, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.rxA_frec_hz = blocks.multiply_const_ff((samp_rate / sps / (2 * math.pi)))
        self.rxA_filtro_adaptado = filter.fft_filter_ccc(1, firdes.root_raised_cosine(1, samp_rate, (samp_rate/sps), excess_bw, (11*sps)), 1)
        self.rxA_errores = blocks.char_to_float(1, 1)
        self.rxA_detector_trama = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code,
          umbral, "packet_len")
        self.rxA_detector_trama.set_min_output_buffer(600000)
        self.rxA_decisor = digital.constellation_decoder_cb(qpsk)
        self.rxA_dec_diferencial = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.rxA_crc = digital.crc32_bb(True, "packet_len", True)
        self.rxA_crc.set_min_output_buffer(70000)
        self.rxA_costas = digital.costas_loop_cc(costas_bw, 4, False)
        self.rxA_comparar = blocks.xor_bb()
        self.rxA_cfo_esperado = analog.sig_source_f((samp_rate/sps), analog.GR_CONST_WAVE, 0, (-cfo_hz), 0, 0)
        self.rxA_ber_ventana = blocks.moving_average_ff(ventana, (1.0/ventana), 4000, 1)
        self.rxA_archivo = blocks.file_sink(gr.sizeof_char*1, "mensajes_recibidos_A.txt", False)
        self.rxA_archivo.set_unbuffered(True)
        self.rxA_alinear = blocks.tagged_stream_align(gr.sizeof_char*1, "inicio_trama")
        self.rxA_a_bytes = blocks.repack_bits_bb(1, 8, "packet_len", True, gr.GR_MSB_FIRST)
        self.rxA_a_bytes.set_min_output_buffer(70000)
        self.rxA_a_bits = blocks.unpack_k_bits_bb(2)
        self.ruido_awgn = analog.noise_source_c(analog.GR_GAUSSIAN, ruido, 0)
        self.osc_rxB = blocks.rotator_cc((2 * math.pi * cfo_hz / samp_rate), False)
        self.osc_rxA = blocks.rotator_cc((-2 * math.pi * cfo_hz / samp_rate), False)
        self.modulo_canal = blocks.complex_to_mag(1)
        self._lbl_teo_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.2e' % x:
            self._lbl_teo_formatter = lambda x: '%.2e' % x
        else:
            self._lbl_teo_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_teo_tool_bar.addWidget(Qt.QLabel("BER teórico: "))
        self._lbl_teo_label = Qt.QLabel(str(self._lbl_teo_formatter(self.lbl_teo)))
        self._lbl_teo_tool_bar.addWidget(self._lbl_teo_label)
        self.top_grid_layout.addWidget(self._lbl_teo_tool_bar, 1, 2, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_ratio_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.2f | %.2f' % x:
            self._lbl_ratio_formatter = lambda x: '%.2f | %.2f' % x
        else:
            self._lbl_ratio_formatter = lambda x: repr(x)

        self._lbl_ratio_tool_bar.addWidget(Qt.QLabel("Medido / teórico (A | B): "))
        self._lbl_ratio_label = Qt.QLabel(str(self._lbl_ratio_formatter(self.lbl_ratio)))
        self._lbl_ratio_tool_bar.addWidget(self._lbl_ratio_label)
        self.top_grid_layout.addWidget(self._lbl_ratio_tool_bar, 1, 5, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(5, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_B_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.2e' % x:
            self._lbl_B_formatter = lambda x: '%.2e' % x
        else:
            self._lbl_B_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_B_tool_bar.addWidget(Qt.QLabel("BER nodo B (acum.): "))
        self._lbl_B_label = Qt.QLabel(str(self._lbl_B_formatter(self.lbl_B)))
        self._lbl_B_tool_bar.addWidget(self._lbl_B_label)
        self.top_grid_layout.addWidget(self._lbl_B_tool_bar, 1, 4, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_A_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.2e' % x:
            self._lbl_A_formatter = lambda x: '%.2e' % x
        else:
            self._lbl_A_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_A_tool_bar.addWidget(Qt.QLabel("BER nodo A (acum.): "))
        self._lbl_A_label = Qt.QLabel(str(self._lbl_A_formatter(self.lbl_A)))
        self._lbl_A_tool_bar.addWidget(self._lbl_A_label)
        self.top_grid_layout.addWidget(self._lbl_A_tool_bar, 1, 3, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.guarda_3 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.guarda_1 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.g_txB = qtgui.time_sink_c(
            200, #size
            samp_rate, #samp_rate
            "Señal que transmite el nodo B", #name
            1, #number of inputs
            None # parent
        )
        self.g_txB.set_update_time(0.10)
        self.g_txB.set_y_axis(-1.25, 1.25)

        self.g_txB.set_y_label('Amplitud', "")

        self.g_txB.enable_tags(True)
        self.g_txB.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_txB.enable_autoscale(False)
        self.g_txB.enable_grid(True)
        self.g_txB.enable_axis_labels(True)
        self.g_txB.enable_control_panel(False)
        self.g_txB.enable_stem_plot(False)


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
                    self.g_txB.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.g_txB.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.g_txB.set_line_label(i, labels[i])
            self.g_txB.set_line_width(i, widths[i])
            self.g_txB.set_line_color(i, colors[i])
            self.g_txB.set_line_style(i, styles[i])
            self.g_txB.set_line_marker(i, markers[i])
            self.g_txB.set_line_alpha(i, alphas[i])

        self._g_txB_win = sip.wrapinstance(self.g_txB.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_txB_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_txA = qtgui.time_sink_c(
            200, #size
            samp_rate, #samp_rate
            "Señal que transmite el nodo A", #name
            1, #number of inputs
            None # parent
        )
        self.g_txA.set_update_time(0.10)
        self.g_txA.set_y_axis(-1.25, 1.25)

        self.g_txA.set_y_label('Amplitud', "")

        self.g_txA.enable_tags(True)
        self.g_txA.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_txA.enable_autoscale(False)
        self.g_txA.enable_grid(True)
        self.g_txA.enable_axis_labels(True)
        self.g_txA.enable_control_panel(False)
        self.g_txA.enable_stem_plot(False)


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
                    self.g_txA.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.g_txA.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.g_txA.set_line_label(i, labels[i])
            self.g_txA.set_line_width(i, widths[i])
            self.g_txA.set_line_color(i, colors[i])
            self.g_txA.set_line_style(i, styles[i])
            self.g_txA.set_line_marker(i, markers[i])
            self.g_txA.set_line_alpha(i, alphas[i])

        self._g_txA_win = sip.wrapinstance(self.g_txA.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_txA_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_turnos = qtgui.time_sink_f(
            (4 * (ranura + guarda)), #size
            samp_rate, #samp_rate
            "Turnos en el canal compartido", #name
            3, #number of inputs
            None # parent
        )
        self.g_turnos.set_update_time(0.10)
        self.g_turnos.set_y_axis(-0.2, 2.0)

        self.g_turnos.set_y_label('Amplitud', "")

        self.g_turnos.enable_tags(False)
        self.g_turnos.set_trigger_mode(qtgui.TRIG_MODE_NORM, qtgui.TRIG_SLOPE_POS, 0.9, 0, 0, "")
        self.g_turnos.enable_autoscale(False)
        self.g_turnos.enable_grid(True)
        self.g_turnos.enable_axis_labels(True)
        self.g_turnos.enable_control_panel(False)
        self.g_turnos.enable_stem_plot(False)


        labels = ['Nodo A transmite', 'Nodo B transmite', '|señal en el canal|', '', '',
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


        for i in range(3):
            if len(labels[i]) == 0:
                self.g_turnos.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_turnos.set_line_label(i, labels[i])
            self.g_turnos.set_line_width(i, widths[i])
            self.g_turnos.set_line_color(i, colors[i])
            self.g_turnos.set_line_style(i, styles[i])
            self.g_turnos.set_line_marker(i, markers[i])
            self.g_turnos.set_line_alpha(i, alphas[i])

        self._g_turnos_win = sip.wrapinstance(self.g_turnos.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_turnos_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(0, 2):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_canal_esp = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Espectro en el canal compartido", #name
            1,
            None # parent
        )
        self.g_canal_esp.set_update_time(0.10)
        self.g_canal_esp.set_y_axis((-100), 10)
        self.g_canal_esp.set_y_label("Potencia relativa", 'dB')
        self.g_canal_esp.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.g_canal_esp.enable_autoscale(False)
        self.g_canal_esp.enable_grid(True)
        self.g_canal_esp.set_fft_average(0.2)
        self.g_canal_esp.enable_axis_labels(True)
        self.g_canal_esp.enable_control_panel(False)
        self.g_canal_esp.set_fft_window_normalized(False)

        self.g_canal_esp.disable_legend()


        labels = ['Canal', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.g_canal_esp.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_canal_esp.set_line_label(i, labels[i])
            self.g_canal_esp.set_line_width(i, widths[i])
            self.g_canal_esp.set_line_color(i, colors[i])
            self.g_canal_esp.set_line_alpha(i, alphas[i])

        self._g_canal_esp_win = sip.wrapinstance(self.g_canal_esp.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_canal_esp_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_canal_const = qtgui.const_sink_c(
            1024, #size
            "Muestras en el canal (con ruido)", #name
            1, #number of inputs
            None # parent
        )
        self.g_canal_const.set_update_time(0.10)
        self.g_canal_const.set_y_axis((-3), 3)
        self.g_canal_const.set_x_axis((-3), 3)
        self.g_canal_const.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.g_canal_const.enable_autoscale(False)
        self.g_canal_const.enable_grid(True)
        self.g_canal_const.enable_axis_labels(True)

        self.g_canal_const.disable_legend()

        labels = ['Canal', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [0.6, 0.6, 0.6, 0.6, 0.6,
            0.6, 0.6, 0.6, 0.6, 0.6]

        for i in range(1):
            if len(labels[i]) == 0:
                self.g_canal_const.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_canal_const.set_line_label(i, labels[i])
            self.g_canal_const.set_line_width(i, widths[i])
            self.g_canal_const.set_line_color(i, colors[i])
            self.g_canal_const.set_line_style(i, styles[i])
            self.g_canal_const.set_line_marker(i, markers[i])
            self.g_canal_const.set_line_alpha(i, alphas[i])

        self._g_canal_const_win = sip.wrapinstance(self.g_canal_const.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_canal_const_win, 1, 2, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self._fase_deg_range = qtgui.Range(-180, 180, 1, 0, 150)
        self._fase_deg_win = qtgui.RangeWidget(self._fase_deg_range, self.set_fase_deg, "Fase del canal [°]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._fase_deg_win, 0, 2, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.fase = blocks.multiply_const_cc(cmath.exp(1j * math.radians(fase_deg)))
        self._ebn0_db_range = qtgui.Range(0, 15, 0.5, 10, 150)
        self._ebn0_db_win = qtgui.RangeWidget(self._ebn0_db_range, self.set_ebn0_db, "Eb/N0 [dB]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._ebn0_db_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.conmutador_rx = blocks.stream_demux(gr.sizeof_gr_complex*1, [ranura, guarda, ranura, guarda])
        def _ber_B_log_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.rxB_sonda_ber.level()
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_ber_B_log,val))
              except AttributeError:
                self.set_ber_B_log(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (4))
        _ber_B_log_thread = threading.Thread(target=_ber_B_log_probe)
        _ber_B_log_thread.daemon = True
        _ber_B_log_thread.start()
        def _ber_A_log_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.rxA_sonda_ber.level()
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_ber_A_log,val))
              except AttributeError:
                self.set_ber_A_log(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (4))
        _ber_A_log_thread = threading.Thread(target=_ber_A_log_probe)
        _ber_A_log_thread.daemon = True
        _ber_A_log_thread.start()
        self.acelerador = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )


        ##################################################
        # Connections
        ##################################################
        self.connect((self.acelerador, 0), (self.fase, 0))
        self.connect((self.acelerador, 0), (self.modulo_canal, 0))
        self.connect((self.conmutador_rx, 1), (self.guarda_1, 0))
        self.connect((self.conmutador_rx, 3), (self.guarda_3, 0))
        self.connect((self.conmutador_rx, 2), (self.osc_rxA, 0))
        self.connect((self.conmutador_rx, 0), (self.osc_rxB, 0))
        self.connect((self.fase, 0), (self.suma_ruido, 0))
        self.connect((self.modulo_canal, 0), (self.g_turnos, 2))
        self.connect((self.osc_rxA, 0), (self.rxA_filtro_adaptado, 0))
        self.connect((self.osc_rxB, 0), (self.rxB_filtro_adaptado, 0))
        self.connect((self.ruido_awgn, 0), (self.suma_ruido, 1))
        self.connect((self.rxA_a_bits, 0), (self.rxA_detector_trama, 0))
        self.connect((self.rxA_a_bits, 0), (self.rxA_marca_preambulo, 0))
        self.connect((self.rxA_a_bytes, 0), (self.rxA_crc, 0))
        self.connect((self.rxA_alinear, 0), (self.rxA_comparar, 0))
        self.connect((self.rxA_alinear, 0), (self.rxA_rx_bit_f, 0))
        self.connect((self.rxA_alinear, 0), (self.rxA_rx_bytes, 0))
        self.connect((self.rxA_ber_ventana, 0), (self.rxA_submuestreo, 0))
        self.connect((self.rxA_cfo_esperado, 0), (self.rxA_g_frec, 1))
        self.connect((self.rxA_comparar, 0), (self.rxA_errores, 0))
        self.connect((self.rxA_costas, 0), (self.rxA_decisor, 0))
        self.connect((self.rxA_costas, 1), (self.rxA_frec_hz, 0))
        self.connect((self.rxA_costas, 0), (self.rxA_g_const, 1))
        self.connect((self.rxA_crc, 0), (self.rxA_una_de_cien, 0))
        self.connect((self.rxA_dec_diferencial, 0), (self.rxA_mapa_gray, 0))
        self.connect((self.rxA_decisor, 0), (self.rxA_dec_diferencial, 0))
        self.connect((self.rxA_detector_trama, 0), (self.rxA_a_bytes, 0))
        self.connect((self.rxA_detector_trama, 0), (self.rxA_payload_f, 0))
        self.connect((self.rxA_errores, 0), (self.rxA_ber_ventana, 0))
        self.connect((self.rxA_errores, 0), (self.rxA_g_bits, 2))
        self.connect((self.rxA_filtro_adaptado, 0), (self.rxA_ojo_interp, 0))
        self.connect((self.rxA_filtro_adaptado, 0), (self.rxA_sinc_simbolo, 0))
        self.connect((self.rxA_frec_hz, 0), (self.rxA_g_frec, 0))
        self.connect((self.rxA_log_ber, 0), (self.rxA_g_ber, 0))
        self.connect((self.rxA_log_teo, 0), (self.rxA_g_ber, 1))
        self.connect((self.rxA_mapa_gray, 0), (self.rxA_a_bits, 0))
        self.connect((self.rxA_marca_preambulo, 0), (self.rxA_alinear, 0))
        self.connect((self.rxA_medidor_ber, 0), (self.rxA_sonda_ber, 0))
        self.connect((self.rxA_ojo_interp, 0), (self.rxA_ojo_re, 0))
        self.connect((self.rxA_ojo_re, 0), (self.rxA_g_ojo, 0))
        self.connect((self.rxA_payload_f, 0), (self.rxA_g_payload, 0))
        self.connect((self.rxA_ref_a_paquetes, 0), (self.rxA_ref_crc, 0))
        self.connect((self.rxA_ref_bit_f, 0), (self.rxA_ref_desplazar, 0))
        self.connect((self.rxA_ref_bits, 0), (self.rxA_ref_saltar_preambulo, 0))
        self.connect((self.rxA_ref_bytes, 0), (self.rxA_medidor_ber, 1))
        self.connect((self.rxA_ref_crc, 0), (self.rxA_ref_encabezado, 0))
        self.connect((self.rxA_ref_crc, 0), (self.rxA_ref_trama, 1))
        self.connect((self.rxA_ref_desplazar, 0), (self.rxA_g_bits, 1))
        self.connect((self.rxA_ref_encabezado, 0), (self.rxA_ref_trama, 0))
        self.connect((self.rxA_ref_fuente, 0), (self.rxA_ref_a_paquetes, 0))
        self.connect((self.rxA_ref_saltar_preambulo, 0), (self.rxA_comparar, 1))
        self.connect((self.rxA_ref_saltar_preambulo, 0), (self.rxA_ref_bit_f, 0))
        self.connect((self.rxA_ref_saltar_preambulo, 0), (self.rxA_ref_bytes, 0))
        self.connect((self.rxA_ref_trama, 0), (self.rxA_ref_bits, 0))
        self.connect((self.rxA_rx_bit_f, 0), (self.rxA_g_bits, 0))
        self.connect((self.rxA_rx_bytes, 0), (self.rxA_medidor_ber, 0))
        self.connect((self.rxA_sinc_simbolo, 0), (self.rxA_costas, 0))
        self.connect((self.rxA_sinc_simbolo, 0), (self.rxA_g_const, 0))
        self.connect((self.rxA_sinc_simbolo, 1), (self.rxA_sinc_null_1, 0))
        self.connect((self.rxA_sinc_simbolo, 2), (self.rxA_sinc_null_2, 0))
        self.connect((self.rxA_sinc_simbolo, 3), (self.rxA_sinc_null_3, 0))
        self.connect((self.rxA_submuestreo, 0), (self.rxA_log_ber, 0))
        self.connect((self.rxA_una_de_cien, 0), (self.rxA_archivo, 0))
        self.connect((self.rxB_a_bits, 0), (self.rxB_detector_trama, 0))
        self.connect((self.rxB_a_bits, 0), (self.rxB_marca_preambulo, 0))
        self.connect((self.rxB_a_bytes, 0), (self.rxB_crc, 0))
        self.connect((self.rxB_alinear, 0), (self.rxB_comparar, 0))
        self.connect((self.rxB_alinear, 0), (self.rxB_rx_bit_f, 0))
        self.connect((self.rxB_alinear, 0), (self.rxB_rx_bytes, 0))
        self.connect((self.rxB_ber_ventana, 0), (self.rxB_submuestreo, 0))
        self.connect((self.rxB_cfo_esperado, 0), (self.rxB_g_frec, 1))
        self.connect((self.rxB_comparar, 0), (self.rxB_errores, 0))
        self.connect((self.rxB_costas, 0), (self.rxB_decisor, 0))
        self.connect((self.rxB_costas, 1), (self.rxB_frec_hz, 0))
        self.connect((self.rxB_costas, 0), (self.rxB_g_const, 1))
        self.connect((self.rxB_crc, 0), (self.rxB_una_de_cien, 0))
        self.connect((self.rxB_dec_diferencial, 0), (self.rxB_mapa_gray, 0))
        self.connect((self.rxB_decisor, 0), (self.rxB_dec_diferencial, 0))
        self.connect((self.rxB_detector_trama, 0), (self.rxB_a_bytes, 0))
        self.connect((self.rxB_detector_trama, 0), (self.rxB_payload_f, 0))
        self.connect((self.rxB_errores, 0), (self.rxB_ber_ventana, 0))
        self.connect((self.rxB_errores, 0), (self.rxB_g_bits, 2))
        self.connect((self.rxB_filtro_adaptado, 0), (self.rxB_ojo_interp, 0))
        self.connect((self.rxB_filtro_adaptado, 0), (self.rxB_sinc_simbolo, 0))
        self.connect((self.rxB_frec_hz, 0), (self.rxB_g_frec, 0))
        self.connect((self.rxB_log_ber, 0), (self.rxB_g_ber, 0))
        self.connect((self.rxB_log_teo, 0), (self.rxB_g_ber, 1))
        self.connect((self.rxB_mapa_gray, 0), (self.rxB_a_bits, 0))
        self.connect((self.rxB_marca_preambulo, 0), (self.rxB_alinear, 0))
        self.connect((self.rxB_medidor_ber, 0), (self.rxB_sonda_ber, 0))
        self.connect((self.rxB_ojo_interp, 0), (self.rxB_ojo_re, 0))
        self.connect((self.rxB_ojo_re, 0), (self.rxB_g_ojo, 0))
        self.connect((self.rxB_payload_f, 0), (self.rxB_g_payload, 0))
        self.connect((self.rxB_ref_a_paquetes, 0), (self.rxB_ref_crc, 0))
        self.connect((self.rxB_ref_bit_f, 0), (self.rxB_ref_desplazar, 0))
        self.connect((self.rxB_ref_bits, 0), (self.rxB_ref_saltar_preambulo, 0))
        self.connect((self.rxB_ref_bytes, 0), (self.rxB_medidor_ber, 1))
        self.connect((self.rxB_ref_crc, 0), (self.rxB_ref_encabezado, 0))
        self.connect((self.rxB_ref_crc, 0), (self.rxB_ref_trama, 1))
        self.connect((self.rxB_ref_desplazar, 0), (self.rxB_g_bits, 1))
        self.connect((self.rxB_ref_encabezado, 0), (self.rxB_ref_trama, 0))
        self.connect((self.rxB_ref_fuente, 0), (self.rxB_ref_a_paquetes, 0))
        self.connect((self.rxB_ref_saltar_preambulo, 0), (self.rxB_comparar, 1))
        self.connect((self.rxB_ref_saltar_preambulo, 0), (self.rxB_ref_bit_f, 0))
        self.connect((self.rxB_ref_saltar_preambulo, 0), (self.rxB_ref_bytes, 0))
        self.connect((self.rxB_ref_trama, 0), (self.rxB_ref_bits, 0))
        self.connect((self.rxB_rx_bit_f, 0), (self.rxB_g_bits, 0))
        self.connect((self.rxB_rx_bytes, 0), (self.rxB_medidor_ber, 0))
        self.connect((self.rxB_sinc_simbolo, 0), (self.rxB_costas, 0))
        self.connect((self.rxB_sinc_simbolo, 0), (self.rxB_g_const, 0))
        self.connect((self.rxB_sinc_simbolo, 1), (self.rxB_sinc_null_1, 0))
        self.connect((self.rxB_sinc_simbolo, 2), (self.rxB_sinc_null_2, 0))
        self.connect((self.rxB_sinc_simbolo, 3), (self.rxB_sinc_null_3, 0))
        self.connect((self.rxB_submuestreo, 0), (self.rxB_log_ber, 0))
        self.connect((self.rxB_una_de_cien, 0), (self.rxB_archivo, 0))
        self.connect((self.silencio_1, 0), (self.turnos, 1))
        self.connect((self.silencio_3, 0), (self.turnos, 3))
        self.connect((self.suma_ruido, 0), (self.conmutador_rx, 0))
        self.connect((self.suma_ruido, 0), (self.g_canal_const, 0))
        self.connect((self.suma_ruido, 0), (self.g_canal_esp, 0))
        self.connect((self.turno_A, 0), (self.g_turnos, 0))
        self.connect((self.turno_B, 0), (self.g_turnos, 1))
        self.connect((self.turnos, 0), (self.acelerador, 0))
        self.connect((self.txA_a_paquetes, 0), (self.txA_crc, 0))
        self.connect((self.txA_crc, 0), (self.txA_encabezado, 0))
        self.connect((self.txA_crc, 0), (self.txA_trama, 1))
        self.connect((self.txA_encabezado, 0), (self.txA_trama, 0))
        self.connect((self.txA_fuente, 0), (self.txA_a_paquetes, 0))
        self.connect((self.txA_modulador, 0), (self.g_txA, 0))
        self.connect((self.txA_modulador, 0), (self.turnos, 0))
        self.connect((self.txA_trama, 0), (self.txA_modulador, 0))
        self.connect((self.txB_a_paquetes, 0), (self.txB_crc, 0))
        self.connect((self.txB_crc, 0), (self.txB_encabezado, 0))
        self.connect((self.txB_crc, 0), (self.txB_trama, 1))
        self.connect((self.txB_encabezado, 0), (self.txB_trama, 0))
        self.connect((self.txB_fuente, 0), (self.txB_a_paquetes, 0))
        self.connect((self.txB_modulador, 0), (self.g_txB, 0))
        self.connect((self.txB_modulador, 0), (self.turnos, 2))
        self.connect((self.txB_trama, 0), (self.txB_modulador, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "halfduplex_4qam")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_ebn0_db(self):
        return self.ebn0_db

    def set_ebn0_db(self, ebn0_db):
        self.ebn0_db = ebn0_db
        self.set_p_qpsk(0.5 * math.erfc(math.sqrt(10**(self.ebn0_db / 10))))
        self.set_ruido(math.sqrt(self.sps / (2 * 10**(self.ebn0_db / 10))))

    def get_p_qpsk(self):
        return self.p_qpsk

    def set_p_qpsk(self, p_qpsk):
        self.p_qpsk = p_qpsk
        self.set_ber_teo(2 * self.p_qpsk * (1 - self.p_qpsk))

    def get_mensaje_B(self):
        return self.mensaje_B

    def set_mensaje_B(self, mensaje_B):
        self.mensaje_B = mensaje_B

    def get_mensaje_A(self):
        return self.mensaje_A

    def set_mensaje_A(self, mensaje_A):
        self.mensaje_A = mensaje_A

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_ruido(math.sqrt(self.sps / (2 * 10**(self.ebn0_db / 10))))
        self.rxA_cfo_esperado.set_sampling_freq((self.samp_rate/self.sps))
        self.rxA_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxA_frec_hz.set_k((self.samp_rate / self.sps / (2 * math.pi)))
        self.rxA_g_ber.set_samp_rate(self.samp_rate/self.sps*2/1000)
        self.rxA_g_bits.set_samp_rate(self.samp_rate/self.sps*2)
        self.rxA_g_frec.set_samp_rate(self.samp_rate/self.sps)
        self.rxA_g_ojo.set_samp_per_symbol((4*self.sps))
        self.rxA_g_payload.set_samp_rate(self.samp_rate/self.sps*2)
        self.rxA_log_teo.set_sampling_freq((self.samp_rate/self.sps*2/1000))
        self.rxA_sinc_simbolo.set_sps(self.sps)
        self.rxB_cfo_esperado.set_sampling_freq((self.samp_rate/self.sps))
        self.rxB_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxB_frec_hz.set_k((self.samp_rate / self.sps / (2 * math.pi)))
        self.rxB_g_ber.set_samp_rate(self.samp_rate/self.sps*2/1000)
        self.rxB_g_bits.set_samp_rate(self.samp_rate/self.sps*2)
        self.rxB_g_frec.set_samp_rate(self.samp_rate/self.sps)
        self.rxB_g_ojo.set_samp_per_symbol((4*self.sps))
        self.rxB_g_payload.set_samp_rate(self.samp_rate/self.sps*2)
        self.rxB_log_teo.set_sampling_freq((self.samp_rate/self.sps*2/1000))
        self.rxB_sinc_simbolo.set_sps(self.sps)

    def get_payload_B(self):
        return self.payload_B

    def set_payload_B(self, payload_B):
        self.payload_B = payload_B
        self.set_L_B(len(self.payload_B))
        self.rxA_ref_fuente.set_data(self.payload_B, [])
        self.txB_fuente.set_data(self.payload_B, [])

    def get_payload_A(self):
        return self.payload_A

    def set_payload_A(self, payload_A):
        self.payload_A = payload_A
        self.set_L_A(len(self.payload_A))
        self.rxB_ref_fuente.set_data(self.payload_A, [])
        self.txA_fuente.set_data(self.payload_A, [])

    def get_ber_teo(self):
        return self.ber_teo

    def set_ber_teo(self, ber_teo):
        self.ber_teo = ber_teo
        self.set_lbl_ratio((10**self.ber_A_log / self.ber_teo, 10**self.ber_B_log / self.ber_teo))
        self.set_lbl_teo(self.ber_teo)
        self.rxA_log_teo.set_amplitude(math.log10(self.ber_teo))
        self.rxB_log_teo.set_amplitude(math.log10(self.ber_teo))

    def get_ber_B_log(self):
        return self.ber_B_log

    def set_ber_B_log(self, ber_B_log):
        self.ber_B_log = ber_B_log
        self.set_lbl_B((10**self.ber_B_log))
        self.set_lbl_ratio((10**self.ber_A_log / self.ber_teo, 10**self.ber_B_log / self.ber_teo))

    def get_ber_A_log(self):
        return self.ber_A_log

    def set_ber_A_log(self, ber_A_log):
        self.ber_A_log = ber_A_log
        self.set_lbl_A((10**self.ber_A_log))
        self.set_lbl_ratio((10**self.ber_A_log / self.ber_teo, 10**self.ber_B_log / self.ber_teo))

    def get_ventana(self):
        return self.ventana

    def set_ventana(self, ventana):
        self.ventana = ventana
        self.rxA_ber_ventana.set_length_and_scale(self.ventana, (1.0/self.ventana))
        self.rxB_ber_ventana.set_length_and_scale(self.ventana, (1.0/self.ventana))

    def get_umbral(self):
        return self.umbral

    def set_umbral(self, umbral):
        self.umbral = umbral
        self.rxA_marca_preambulo.set_threshold(self.umbral)
        self.rxB_marca_preambulo.set_threshold(self.umbral)

    def get_sync_bw(self):
        return self.sync_bw

    def set_sync_bw(self, sync_bw):
        self.sync_bw = sync_bw
        self.rxA_sinc_simbolo.set_loop_bandwidth(self.sync_bw)
        self.rxB_sinc_simbolo.set_loop_bandwidth(self.sync_bw)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.acelerador.set_sample_rate(self.samp_rate)
        self.g_canal_esp.set_frequency_range(0, self.samp_rate)
        self.g_turnos.set_samp_rate(self.samp_rate)
        self.g_txA.set_samp_rate(self.samp_rate)
        self.g_txB.set_samp_rate(self.samp_rate)
        self.osc_rxA.set_phase_inc((-2 * math.pi * self.cfo_hz / self.samp_rate))
        self.osc_rxB.set_phase_inc((2 * math.pi * self.cfo_hz / self.samp_rate))
        self.rxA_cfo_esperado.set_sampling_freq((self.samp_rate/self.sps))
        self.rxA_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxA_frec_hz.set_k((self.samp_rate / self.sps / (2 * math.pi)))
        self.rxA_g_ber.set_samp_rate(self.samp_rate/self.sps*2/1000)
        self.rxA_g_bits.set_samp_rate(self.samp_rate/self.sps*2)
        self.rxA_g_frec.set_samp_rate(self.samp_rate/self.sps)
        self.rxA_g_ojo.set_samp_rate(4*self.samp_rate)
        self.rxA_g_payload.set_samp_rate(self.samp_rate/self.sps*2)
        self.rxA_log_teo.set_sampling_freq((self.samp_rate/self.sps*2/1000))
        self.rxB_cfo_esperado.set_sampling_freq((self.samp_rate/self.sps))
        self.rxB_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxB_frec_hz.set_k((self.samp_rate / self.sps / (2 * math.pi)))
        self.rxB_g_ber.set_samp_rate(self.samp_rate/self.sps*2/1000)
        self.rxB_g_bits.set_samp_rate(self.samp_rate/self.sps*2)
        self.rxB_g_frec.set_samp_rate(self.samp_rate/self.sps)
        self.rxB_g_ojo.set_samp_rate(4*self.samp_rate)
        self.rxB_g_payload.set_samp_rate(self.samp_rate/self.sps*2)
        self.rxB_log_teo.set_sampling_freq((self.samp_rate/self.sps*2/1000))

    def get_ruido(self):
        return self.ruido

    def set_ruido(self, ruido):
        self.ruido = ruido
        self.ruido_awgn.set_amplitude(self.ruido)

    def get_ranura(self):
        return self.ranura

    def set_ranura(self, ranura):
        self.ranura = ranura
        self.turno_A.set_data([1.8] * self.ranura + [0.0] * (self.guarda + self.ranura + self.guarda), [])
        self.turno_B.set_data([0.0] * (self.ranura + self.guarda) + [1.8] * self.ranura + [0.0] * self.guarda, [])

    def get_qpsk(self):
        return self.qpsk

    def set_qpsk(self, qpsk):
        self.qpsk = qpsk
        self.rxA_decisor.set_constellation(self.qpsk)
        self.rxB_decisor.set_constellation(self.qpsk)

    def get_lbl_teo(self):
        return self.lbl_teo

    def set_lbl_teo(self, lbl_teo):
        self.lbl_teo = lbl_teo
        Qt.QMetaObject.invokeMethod(self._lbl_teo_label, "setText", Qt.Q_ARG("QString", str(self._lbl_teo_formatter(self.lbl_teo))))

    def get_lbl_ratio(self):
        return self.lbl_ratio

    def set_lbl_ratio(self, lbl_ratio):
        self.lbl_ratio = lbl_ratio
        Qt.QMetaObject.invokeMethod(self._lbl_ratio_label, "setText", Qt.Q_ARG("QString", str(self._lbl_ratio_formatter(self.lbl_ratio))))

    def get_lbl_B(self):
        return self.lbl_B

    def set_lbl_B(self, lbl_B):
        self.lbl_B = lbl_B
        Qt.QMetaObject.invokeMethod(self._lbl_B_label, "setText", Qt.Q_ARG("QString", str(self._lbl_B_formatter(self.lbl_B))))

    def get_lbl_A(self):
        return self.lbl_A

    def set_lbl_A(self, lbl_A):
        self.lbl_A = lbl_A
        Qt.QMetaObject.invokeMethod(self._lbl_A_label, "setText", Qt.Q_ARG("QString", str(self._lbl_A_formatter(self.lbl_A))))

    def get_guarda(self):
        return self.guarda

    def set_guarda(self, guarda):
        self.guarda = guarda
        self.turno_A.set_data([1.8] * self.ranura + [0.0] * (self.guarda + self.ranura + self.guarda), [])
        self.turno_B.set_data([0.0] * (self.ranura + self.guarda) + [1.8] * self.ranura + [0.0] * self.guarda, [])

    def get_formato_trama(self):
        return self.formato_trama

    def set_formato_trama(self, formato_trama):
        self.formato_trama = formato_trama
        self.rxA_ref_encabezado.set_header_format(self.formato_trama)
        self.rxB_ref_encabezado.set_header_format(self.formato_trama)
        self.txA_encabezado.set_header_format(self.formato_trama)
        self.txB_encabezado.set_header_format(self.formato_trama)

    def get_fase_deg(self):
        return self.fase_deg

    def set_fase_deg(self, fase_deg):
        self.fase_deg = fase_deg
        self.fase.set_k(cmath.exp(1j * math.radians(self.fase_deg)))

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw
        self.rxA_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxB_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_costas_bw(self):
        return self.costas_bw

    def set_costas_bw(self, costas_bw):
        self.costas_bw = costas_bw
        self.rxA_costas.set_loop_bandwidth(self.costas_bw)
        self.rxB_costas.set_loop_bandwidth(self.costas_bw)

    def get_cfo_hz(self):
        return self.cfo_hz

    def set_cfo_hz(self, cfo_hz):
        self.cfo_hz = cfo_hz
        self.osc_rxA.set_phase_inc((-2 * math.pi * self.cfo_hz / self.samp_rate))
        self.osc_rxB.set_phase_inc((2 * math.pi * self.cfo_hz / self.samp_rate))
        self.rxA_cfo_esperado.set_amplitude((-self.cfo_hz))
        self.rxB_cfo_esperado.set_amplitude(self.cfo_hz)

    def get_L_B(self):
        return self.L_B

    def set_L_B(self, L_B):
        self.L_B = L_B
        self.rxA_ref_a_paquetes.set_packet_len(self.L_B)
        self.rxA_ref_a_paquetes.set_packet_len_pmt(self.L_B)
        self.rxA_una_de_cien.set_m(self.L_B)
        self.rxA_una_de_cien.set_n((100*self.L_B))
        self.txB_a_paquetes.set_packet_len(self.L_B)
        self.txB_a_paquetes.set_packet_len_pmt(self.L_B)

    def get_L_A(self):
        return self.L_A

    def set_L_A(self, L_A):
        self.L_A = L_A
        self.rxB_ref_a_paquetes.set_packet_len(self.L_A)
        self.rxB_ref_a_paquetes.set_packet_len_pmt(self.L_A)
        self.rxB_una_de_cien.set_m(self.L_A)
        self.rxB_una_de_cien.set_n((100*self.L_A))
        self.txA_a_paquetes.set_packet_len(self.L_A)
        self.txA_a_paquetes.set_packet_len_pmt(self.L_A)




def main(top_block_cls=halfduplex_4qam, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

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
