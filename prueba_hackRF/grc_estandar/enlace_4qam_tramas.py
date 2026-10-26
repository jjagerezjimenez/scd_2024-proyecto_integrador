#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Enlace 4-QAM con tramas y BER (bloques estándar)
# Author: Juan Gerez
# Description: Enlace 4-QAM con tramas (preámbulo + longitud + CRC-32) y medición de BER, solo bloques estándar de GNU Radio
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
from gnuradio import gr, pdu
import math, cmath
import sip
import threading
import time



class enlace_4qam_tramas(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Enlace 4-QAM con tramas y BER (bloques estándar)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Enlace 4-QAM con tramas y BER (bloques estándar)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "enlace_4qam_tramas")

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
        self.mensaje = mensaje = "Sistemas de Comunicaciones Digitales - FACET UNT - enlace 4-QAM half-duplex en GNU Radio!!!!!!!!"
        self.ebn0_db = ebn0_db = 10
        self.payload = payload = list(mensaje.encode())
        self.p_qpsk = p_qpsk = 0.5 * math.erfc(math.sqrt(10**(ebn0_db / 10)))
        self.sps = sps = 4
        self.ber_teo = ber_teo = 2 * p_qpsk * (1 - p_qpsk)
        self.ber_rec = ber_rec = 0
        self.ber_acum_log = ber_acum_log = 0
        self.L = L = len(payload)
        self.ventana = ventana = 1000000
        self.umbral = umbral = 12
        self.sync_bw = sync_bw = 0.01
        self.samp_rate = samp_rate = 500000
        self.ruido = ruido = math.sqrt(sps / (2 * 10**(ebn0_db / 10)))
        self.qpsk = qpsk = digital.constellation_rect([-0.707-0.707j, 0.707-0.707j, +0.707+0.707j, -0.707+0.707j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.lbl_teo = lbl_teo = ber_teo
        self.lbl_rec = lbl_rec = ber_rec
        self.lbl_ratio = lbl_ratio = (ber_rec / ber_teo)
        self.lbl_acum = lbl_acum = (10**ber_acum_log)
        self.formato_trama = formato_trama = digital.header_format_default(digital.packet_utils.default_access_code,0, 1)
        self.fase_deg = fase_deg = 0
        self.excess_bw = excess_bw = 0.35
        self.costas_bw = costas_bw = 0.005
        self.cfo_hz = cfo_hz = 0
        self.bits_trama = bits_trama = 8*(8 + 4 + L + 4)

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
        self.sonda_ber_ventana = blocks.probe_signal_f()
        self.sonda_ber_acum = blocks.probe_signal_f()
        self.pestanas = Qt.QTabWidget()
        self.pestanas_widget_0 = Qt.QWidget()
        self.pestanas_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_0)
        self.pestanas_grid_layout_0 = Qt.QGridLayout()
        self.pestanas_layout_0.addLayout(self.pestanas_grid_layout_0)
        self.pestanas.addTab(self.pestanas_widget_0, '1. Transmisor y canal')
        self.pestanas_widget_1 = Qt.QWidget()
        self.pestanas_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_1)
        self.pestanas_grid_layout_1 = Qt.QGridLayout()
        self.pestanas_layout_1.addLayout(self.pestanas_grid_layout_1)
        self.pestanas.addTab(self.pestanas_widget_1, '2. Receptor: filtro adaptado y sincronismo')
        self.pestanas_widget_2 = Qt.QWidget()
        self.pestanas_layout_2 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_2)
        self.pestanas_grid_layout_2 = Qt.QGridLayout()
        self.pestanas_layout_2.addLayout(self.pestanas_grid_layout_2)
        self.pestanas.addTab(self.pestanas_widget_2, '3. Tramas, bits y BER')
        self.top_grid_layout.addWidget(self.pestanas, 2, 0, 1, 6)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._cfo_hz_range = qtgui.Range(-1000, 1000, 10, 0, 150)
        self._cfo_hz_win = qtgui.RangeWidget(self._cfo_hz_range, self.set_cfo_hz, "CFO [Hz]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._cfo_hz_win, 0, 4, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.una_de_cien = blocks.keep_m_in_n(gr.sizeof_char, L, (100*L), 0)
        self.tx_re = blocks.complex_to_real(1)
        self.trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.suma_ruido = blocks.add_vcc(1)
        self.submuestreo = blocks.keep_one_in_n(gr.sizeof_float*1, 1000)
        self.sinc_simbolo = digital.symbol_sync_cc(
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
        self.sinc_err_null = blocks.null_sink(gr.sizeof_float*1)
        self.rx_re = blocks.complex_to_real(1)
        self.rx_bytes_ber = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rx_bit_float = blocks.char_to_float(1, 1)
        self.ruido_awgn = analog.noise_source_c(analog.GR_GAUSSIAN, ruido, 0)
        self.ref_trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.ref_saltar_preambulo = blocks.skiphead(gr.sizeof_char*1, 64)
        self.ref_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, L, "packet_len")
        self.ref_fuente = blocks.vector_source_b(payload, True, 1, [])
        self.ref_encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self.ref_desplazar = blocks.add_const_ff(1.5)
        self.ref_crc = digital.crc32_bb(False, "packet_len", True)
        self.ref_bytes_ber = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.ref_bits = blocks.unpack_k_bits_bb(8)
        self.ref_bit_float = blocks.char_to_float(1, 1)
        self.payload_float = blocks.char_to_float(1, 1)
        self.ojo_interp = filter.rational_resampler_ccc(
                interpolation=4,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.modulador = digital.generic_mod(
            constellation=qpsk,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=excess_bw,
            verbose=False,
            log=False,
            truncate=False)
        self.mf_re = blocks.complex_to_real(1)
        self.medidor_ber = fec.ber_bf(False, 100, -7.0)
        self.marca_preambulo = digital.correlate_access_code_tag_bb(digital.packet_utils.default_access_code, umbral, "inicio_trama")
        self.mapa_gray = digital.map_bb([0, 1, 3, 2])
        self.log_teo = analog.sig_source_f((samp_rate/sps*2/1000), analog.GR_CONST_WAVE, 0, math.log10(ber_teo), 0, 0)
        self.log_ber = blocks.nlog10_ff(1, 1, 0)
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
        self._lbl_rec_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.2e' % x:
            self._lbl_rec_formatter = lambda x: '%.2e' % x
        else:
            self._lbl_rec_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_rec_tool_bar.addWidget(Qt.QLabel("BER medido (último Mbit): "))
        self._lbl_rec_label = Qt.QLabel(str(self._lbl_rec_formatter(self.lbl_rec)))
        self._lbl_rec_tool_bar.addWidget(self._lbl_rec_label)
        self.top_grid_layout.addWidget(self._lbl_rec_tool_bar, 1, 4, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_ratio_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.2f' % x:
            self._lbl_ratio_formatter = lambda x: '%.2f' % x
        else:
            self._lbl_ratio_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_ratio_tool_bar.addWidget(Qt.QLabel("Medido (último Mbit) / teórico: "))
        self._lbl_ratio_label = Qt.QLabel(str(self._lbl_ratio_formatter(self.lbl_ratio)))
        self._lbl_ratio_tool_bar.addWidget(self._lbl_ratio_label)
        self.top_grid_layout.addWidget(self._lbl_ratio_tool_bar, 1, 5, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(5, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_acum_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.2e' % x:
            self._lbl_acum_formatter = lambda x: '%.2e' % x
        else:
            self._lbl_acum_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_acum_tool_bar.addWidget(Qt.QLabel("BER medido (acum.): "))
        self._lbl_acum_label = Qt.QLabel(str(self._lbl_acum_formatter(self.lbl_acum)))
        self._lbl_acum_tool_bar.addWidget(self._lbl_acum_label)
        self.top_grid_layout.addWidget(self._lbl_acum_tool_bar, 1, 3, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.g_tx_iq = qtgui.time_sink_c(
            200, #size
            samp_rate, #samp_rate
            "Señal TX (salida del modulador)", #name
            1, #number of inputs
            None # parent
        )
        self.g_tx_iq.set_update_time(0.10)
        self.g_tx_iq.set_y_axis(-1.25, 1.25)

        self.g_tx_iq.set_y_label('Amplitud', "")

        self.g_tx_iq.enable_tags(True)
        self.g_tx_iq.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_tx_iq.enable_autoscale(False)
        self.g_tx_iq.enable_grid(True)
        self.g_tx_iq.enable_axis_labels(True)
        self.g_tx_iq.enable_control_panel(False)
        self.g_tx_iq.enable_stem_plot(False)


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
                    self.g_tx_iq.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.g_tx_iq.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.g_tx_iq.set_line_label(i, labels[i])
            self.g_tx_iq.set_line_width(i, widths[i])
            self.g_tx_iq.set_line_color(i, colors[i])
            self.g_tx_iq.set_line_style(i, styles[i])
            self.g_tx_iq.set_line_marker(i, markers[i])
            self.g_tx_iq.set_line_alpha(i, alphas[i])

        self._g_tx_iq_win = sip.wrapinstance(self.g_tx_iq.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_tx_iq_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_tx_esp = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Espectro de la señal TX", #name
            1,
            None # parent
        )
        self.g_tx_esp.set_update_time(0.10)
        self.g_tx_esp.set_y_axis((-100), 10)
        self.g_tx_esp.set_y_label("Potencia relativa", 'dB')
        self.g_tx_esp.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.g_tx_esp.enable_autoscale(False)
        self.g_tx_esp.enable_grid(True)
        self.g_tx_esp.set_fft_average(0.2)
        self.g_tx_esp.enable_axis_labels(True)
        self.g_tx_esp.enable_control_panel(False)
        self.g_tx_esp.set_fft_window_normalized(False)

        self.g_tx_esp.disable_legend()


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
                self.g_tx_esp.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_tx_esp.set_line_label(i, labels[i])
            self.g_tx_esp.set_line_width(i, widths[i])
            self.g_tx_esp.set_line_color(i, colors[i])
            self.g_tx_esp.set_line_alpha(i, alphas[i])

        self._g_tx_esp_win = sip.wrapinstance(self.g_tx_esp.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_tx_esp_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_sync_const = qtgui.const_sink_c(
            1024, #size
            "Constelación antes y después de Costas", #name
            2, #number of inputs
            None # parent
        )
        self.g_sync_const.set_update_time(0.10)
        self.g_sync_const.set_y_axis((-1.5), 1.5)
        self.g_sync_const.set_x_axis((-1.5), 1.5)
        self.g_sync_const.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.g_sync_const.enable_autoscale(False)
        self.g_sync_const.enable_grid(True)
        self.g_sync_const.enable_axis_labels(True)


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
                self.g_sync_const.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_sync_const.set_line_label(i, labels[i])
            self.g_sync_const.set_line_width(i, widths[i])
            self.g_sync_const.set_line_color(i, colors[i])
            self.g_sync_const.set_line_style(i, styles[i])
            self.g_sync_const.set_line_marker(i, markers[i])
            self.g_sync_const.set_line_alpha(i, alphas[i])

        self._g_sync_const_win = sip.wrapinstance(self.g_sync_const.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._g_sync_const_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.g_periodo = qtgui.time_sink_f(
            2000, #size
            samp_rate/sps, #samp_rate
            "Período de símbolo estimado [muestras]", #name
            2, #number of inputs
            None # parent
        )
        self.g_periodo.set_update_time(0.10)
        self.g_periodo.set_y_axis(3.5, 4.5)

        self.g_periodo.set_y_label('Muestras', "")

        self.g_periodo.enable_tags(False)
        self.g_periodo.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_periodo.enable_autoscale(False)
        self.g_periodo.enable_grid(True)
        self.g_periodo.enable_axis_labels(True)
        self.g_periodo.enable_control_panel(False)
        self.g_periodo.enable_stem_plot(False)


        labels = ['Instantáneo', 'Promedio', '', '', '',
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
                self.g_periodo.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_periodo.set_line_label(i, labels[i])
            self.g_periodo.set_line_width(i, widths[i])
            self.g_periodo.set_line_color(i, colors[i])
            self.g_periodo.set_line_style(i, styles[i])
            self.g_periodo.set_line_marker(i, markers[i])
            self.g_periodo.set_line_alpha(i, alphas[i])

        self._g_periodo_win = sip.wrapinstance(self.g_periodo.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._g_periodo_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.g_payload = qtgui.time_sink_f(
            (2 * 8 * (L + 4)), #size
            samp_rate/sps*2, #samp_rate
            "Payload del detector de tramas", #name
            1, #number of inputs
            None # parent
        )
        self.g_payload.set_update_time(0.10)
        self.g_payload.set_y_axis(-0.5, 1.5)

        self.g_payload.set_y_label('Bit', "")

        self.g_payload.enable_tags(True)
        self.g_payload.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_payload.enable_autoscale(False)
        self.g_payload.enable_grid(True)
        self.g_payload.enable_axis_labels(True)
        self.g_payload.enable_control_panel(False)
        self.g_payload.enable_stem_plot(False)

        self.g_payload.disable_legend()

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
                self.g_payload.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_payload.set_line_label(i, labels[i])
            self.g_payload.set_line_width(i, widths[i])
            self.g_payload.set_line_color(i, colors[i])
            self.g_payload.set_line_style(i, styles[i])
            self.g_payload.set_line_marker(i, markers[i])
            self.g_payload.set_line_alpha(i, alphas[i])

        self._g_payload_win = sip.wrapinstance(self.g_payload.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._g_payload_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.g_ojo = qtgui.eye_sink_f(
            2048, #size
            4*samp_rate, #samp_rate
            1, #number of inputs
            None
        )
        self.g_ojo.set_update_time(0.10)
        self.g_ojo.set_samp_per_symbol((4*sps))
        self.g_ojo.set_y_axis(-1.5, 1.5)

        self.g_ojo.set_y_label("Amplitud", "")

        self.g_ojo.enable_tags(False)
        self.g_ojo.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_ojo.enable_autoscale(False)
        self.g_ojo.enable_grid(True)
        self.g_ojo.enable_axis_labels(True)
        self.g_ojo.enable_control_panel(False)


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
                self.g_ojo.set_line_label(i, "Eye[Data {0}]".format(i))
            else:
                self.g_ojo.set_line_label(i, labels[i])
            self.g_ojo.set_line_width(i, widths[i])
            self.g_ojo.set_line_color(i, colors[i])
            self.g_ojo.set_line_style(i, styles[i])
            self.g_ojo.set_line_marker(i, markers[i])
            self.g_ojo.set_line_alpha(i, alphas[i])

        self._g_ojo_win = sip.wrapinstance(self.g_ojo.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._g_ojo_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.g_mf_t = qtgui.time_sink_c(
            160, #size
            samp_rate, #samp_rate
            "Salida del filtro adaptado", #name
            1, #number of inputs
            None # parent
        )
        self.g_mf_t.set_update_time(0.10)
        self.g_mf_t.set_y_axis(-1.25, 1.25)

        self.g_mf_t.set_y_label('Amplitud', "")

        self.g_mf_t.enable_tags(True)
        self.g_mf_t.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_mf_t.enable_autoscale(False)
        self.g_mf_t.enable_grid(True)
        self.g_mf_t.enable_axis_labels(True)
        self.g_mf_t.enable_control_panel(False)
        self.g_mf_t.enable_stem_plot(False)


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
                    self.g_mf_t.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.g_mf_t.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.g_mf_t.set_line_label(i, labels[i])
            self.g_mf_t.set_line_width(i, widths[i])
            self.g_mf_t.set_line_color(i, colors[i])
            self.g_mf_t.set_line_style(i, styles[i])
            self.g_mf_t.set_line_marker(i, markers[i])
            self.g_mf_t.set_line_alpha(i, alphas[i])

        self._g_mf_t_win = sip.wrapinstance(self.g_mf_t.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._g_mf_t_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.g_histograma = qtgui.histogram_sink_f(
            4000,
            120,
            (-1.5),
            1.5,
            "Histograma de I tras Costas",
            1,
            None # parent
        )

        self.g_histograma.set_update_time(0.20)
        self.g_histograma.enable_autoscale(True)
        self.g_histograma.enable_accumulate(False)
        self.g_histograma.enable_grid(True)
        self.g_histograma.enable_axis_labels(True)

        self.g_histograma.disable_legend()

        labels = ['Componente I', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "blue", "blue", "blue", "blue",
            "blue", "blue", "blue", "blue", "blue"]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers= [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.g_histograma.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_histograma.set_line_label(i, labels[i])
            self.g_histograma.set_line_width(i, widths[i])
            self.g_histograma.set_line_color(i, colors[i])
            self.g_histograma.set_line_style(i, styles[i])
            self.g_histograma.set_line_marker(i, markers[i])
            self.g_histograma.set_line_alpha(i, alphas[i])

        self._g_histograma_win = sip.wrapinstance(self.g_histograma.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._g_histograma_win, 1, 2, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.g_frec = qtgui.time_sink_f(
            2000, #size
            samp_rate/sps, #samp_rate
            "Frecuencia de Costas vs CFO [Hz]", #name
            2, #number of inputs
            None # parent
        )
        self.g_frec.set_update_time(0.10)
        self.g_frec.set_y_axis(-1100, 1100)

        self.g_frec.set_y_label('Hz', "")

        self.g_frec.enable_tags(False)
        self.g_frec.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_frec.enable_autoscale(False)
        self.g_frec.enable_grid(True)
        self.g_frec.enable_axis_labels(True)
        self.g_frec.enable_control_panel(False)
        self.g_frec.enable_stem_plot(False)


        labels = ['Costas', 'CFO canal', '', '', '',
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
                self.g_frec.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_frec.set_line_label(i, labels[i])
            self.g_frec.set_line_width(i, widths[i])
            self.g_frec.set_line_color(i, colors[i])
            self.g_frec.set_line_style(i, styles[i])
            self.g_frec.set_line_marker(i, markers[i])
            self.g_frec.set_line_alpha(i, alphas[i])

        self._g_frec_win = sip.wrapinstance(self.g_frec.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._g_frec_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.g_canal_t = qtgui.time_sink_f(
            200, #size
            samp_rate, #samp_rate
            "Componente I: TX vs RX", #name
            2, #number of inputs
            None # parent
        )
        self.g_canal_t.set_update_time(0.10)
        self.g_canal_t.set_y_axis(-2.5, 2.5)

        self.g_canal_t.set_y_label('Amplitud', "")

        self.g_canal_t.enable_tags(True)
        self.g_canal_t.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_canal_t.enable_autoscale(False)
        self.g_canal_t.enable_grid(True)
        self.g_canal_t.enable_axis_labels(True)
        self.g_canal_t.enable_control_panel(False)
        self.g_canal_t.enable_stem_plot(False)


        labels = ['TX', 'RX', '', '', '',
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
                self.g_canal_t.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_canal_t.set_line_label(i, labels[i])
            self.g_canal_t.set_line_width(i, widths[i])
            self.g_canal_t.set_line_color(i, colors[i])
            self.g_canal_t.set_line_style(i, styles[i])
            self.g_canal_t.set_line_marker(i, markers[i])
            self.g_canal_t.set_line_alpha(i, alphas[i])

        self._g_canal_t_win = sip.wrapinstance(self.g_canal_t.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_canal_t_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_canal_esp = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Espectro TX vs RX", #name
            2,
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



        labels = ['TX', 'RX', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(2):
            if len(labels[i]) == 0:
                self.g_canal_esp.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_canal_esp.set_line_label(i, labels[i])
            self.g_canal_esp.set_line_width(i, widths[i])
            self.g_canal_esp.set_line_color(i, colors[i])
            self.g_canal_esp.set_line_alpha(i, alphas[i])

        self._g_canal_esp_win = sip.wrapinstance(self.g_canal_esp.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_canal_esp_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_canal_const = qtgui.const_sink_c(
            1024, #size
            "Muestras RX sin sincronizar", #name
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

        labels = ['RX', '', '', '', '',
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
        self.g_bits_tx = qtgui.time_sink_f(
            160, #size
            samp_rate/sps*2, #samp_rate
            "Trama TX: preámbulo + longitud + datos", #name
            1, #number of inputs
            None # parent
        )
        self.g_bits_tx.set_update_time(0.10)
        self.g_bits_tx.set_y_axis(-0.5, 1.5)

        self.g_bits_tx.set_y_label('Bit', "")

        self.g_bits_tx.enable_tags(True)
        self.g_bits_tx.set_trigger_mode(qtgui.TRIG_MODE_TAG, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "packet_len")
        self.g_bits_tx.enable_autoscale(False)
        self.g_bits_tx.enable_grid(True)
        self.g_bits_tx.enable_axis_labels(True)
        self.g_bits_tx.enable_control_panel(False)
        self.g_bits_tx.enable_stem_plot(True)

        self.g_bits_tx.disable_legend()

        labels = ['Bits transmitidos', '', '', '', '',
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
                self.g_bits_tx.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_bits_tx.set_line_label(i, labels[i])
            self.g_bits_tx.set_line_width(i, widths[i])
            self.g_bits_tx.set_line_color(i, colors[i])
            self.g_bits_tx.set_line_style(i, styles[i])
            self.g_bits_tx.set_line_marker(i, markers[i])
            self.g_bits_tx.set_line_alpha(i, alphas[i])

        self._g_bits_tx_win = sip.wrapinstance(self.g_bits_tx.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_bits_tx_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_bits = qtgui.time_sink_f(
            200, #size
            samp_rate/sps*2, #samp_rate
            "Bits RX vs TX (+1,5) y errores", #name
            3, #number of inputs
            None # parent
        )
        self.g_bits.set_update_time(0.10)
        self.g_bits.set_y_axis(-1, 4)

        self.g_bits.set_y_label('Bit', "")

        self.g_bits.enable_tags(False)
        self.g_bits.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_bits.enable_autoscale(False)
        self.g_bits.enable_grid(True)
        self.g_bits.enable_axis_labels(True)
        self.g_bits.enable_control_panel(False)
        self.g_bits.enable_stem_plot(False)


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
                self.g_bits.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_bits.set_line_label(i, labels[i])
            self.g_bits.set_line_width(i, widths[i])
            self.g_bits.set_line_color(i, colors[i])
            self.g_bits.set_line_style(i, styles[i])
            self.g_bits.set_line_marker(i, markers[i])
            self.g_bits.set_line_alpha(i, alphas[i])

        self._g_bits_win = sip.wrapinstance(self.g_bits.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._g_bits_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.g_ber_t = qtgui.time_sink_f(
            500, #size
            samp_rate/sps*2/1000, #samp_rate
            "log10(BER): medido vs teórico", #name
            2, #number of inputs
            None # parent
        )
        self.g_ber_t.set_update_time(0.10)
        self.g_ber_t.set_y_axis(-6, 0)

        self.g_ber_t.set_y_label('log10(BER)', "")

        self.g_ber_t.enable_tags(False)
        self.g_ber_t.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_ber_t.enable_autoscale(False)
        self.g_ber_t.enable_grid(True)
        self.g_ber_t.enable_axis_labels(True)
        self.g_ber_t.enable_control_panel(False)
        self.g_ber_t.enable_stem_plot(False)


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
                self.g_ber_t.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_ber_t.set_line_label(i, labels[i])
            self.g_ber_t.set_line_width(i, widths[i])
            self.g_ber_t.set_line_color(i, colors[i])
            self.g_ber_t.set_line_style(i, styles[i])
            self.g_ber_t.set_line_marker(i, markers[i])
            self.g_ber_t.set_line_alpha(i, alphas[i])

        self._g_ber_t_win = sip.wrapinstance(self.g_ber_t.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._g_ber_t_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.g_ber_num = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.g_ber_num.set_update_time(0.20)
        self.g_ber_num.set_title("log10(BER) acumulado")

        labels = ['Acumulado', '', '', '', '',
            '', '', '', '', '']
        units = ['', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.g_ber_num.set_min(i, -7)
            self.g_ber_num.set_max(i, 0)
            self.g_ber_num.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.g_ber_num.set_label(i, "Data {0}".format(i))
            else:
                self.g_ber_num.set_label(i, labels[i])
            self.g_ber_num.set_unit(i, units[i])
            self.g_ber_num.set_factor(i, factor[i])

        self.g_ber_num.enable_autoscale(False)
        self._g_ber_num_win = sip.wrapinstance(self.g_ber_num.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._g_ber_num_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.fuente = blocks.vector_source_b(payload, True, 1, [])
        self.frec_hz = blocks.multiply_const_ff((samp_rate / sps / (2 * math.pi)))
        self.filtro_adaptado = filter.fft_filter_ccc(1, firdes.root_raised_cosine(1, samp_rate, (samp_rate/sps), excess_bw, (11*sps)), 1)
        self._fase_deg_range = qtgui.Range(-180, 180, 1, 0, 150)
        self._fase_deg_win = qtgui.RangeWidget(self._fase_deg_range, self.set_fase_deg, "Fase del canal [°]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._fase_deg_win, 0, 2, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.fase = blocks.multiply_const_cc(cmath.exp(1j * math.radians(fase_deg)))
        self.errores_float = blocks.char_to_float(1, 1)
        self.encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self._ebn0_db_range = qtgui.Range(0, 15, 0.5, 10, 150)
        self._ebn0_db_win = qtgui.RangeWidget(self._ebn0_db_range, self.set_ebn0_db, "Eb/N0 [dB]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._ebn0_db_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.detector_trama = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code,
          umbral, "packet_len")
        self.detector_trama.set_min_output_buffer(600000)
        self.decisor = digital.constellation_decoder_cb(qpsk)
        self.dec_diferencial = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.crc_tx = digital.crc32_bb(False, "packet_len", True)
        self.crc_rx = digital.crc32_bb(True, "packet_len", True)
        self.crc_rx.set_min_output_buffer(70000)
        self.costas_re = blocks.complex_to_real(1)
        self._costas_bw_range = qtgui.Range(0.001, 0.1, 0.001, 0.005, 100)
        self._costas_bw_win = qtgui.RangeWidget(self._costas_bw_range, self.set_costas_bw, "BW lazo de Costas", "counter", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._costas_bw_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.costas = digital.costas_loop_cc(costas_bw, 4, False)
        self.comparar = blocks.xor_bb()
        self.cfo_real = analog.sig_source_f((samp_rate/sps), analog.GR_CONST_WAVE, 0, cfo_hz, 0, 0)
        self.cfo = blocks.rotator_cc((2 * math.pi * cfo_hz / samp_rate), False)
        self.bits_tx_unpack = blocks.unpack_k_bits_bb(8)
        self.bits_tx_float = blocks.char_to_float(1, 1)
        self.ber_ventana = blocks.moving_average_ff(ventana, (1.0/ventana), 4000, 1)
        def _ber_rec_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.sonda_ber_ventana.level()
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_ber_rec,val))
              except AttributeError:
                self.set_ber_rec(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (4))
        _ber_rec_thread = threading.Thread(target=_ber_rec_probe)
        _ber_rec_thread.daemon = True
        _ber_rec_thread.start()
        def _ber_acum_log_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.sonda_ber_acum.level()
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_ber_acum_log,val))
              except AttributeError:
                self.set_ber_acum_log(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (4))
        _ber_acum_log_thread = threading.Thread(target=_ber_acum_log_probe)
        _ber_acum_log_thread.daemon = True
        _ber_acum_log_thread.start()
        self.archivo_mensajes = blocks.file_sink(gr.sizeof_char*1, "mensajes_recibidos.txt", False)
        self.archivo_mensajes.set_unbuffered(True)
        self.alinear = blocks.tagged_stream_align(gr.sizeof_char*1, "inicio_trama")
        self.acelerador = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.a_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, "packet_len")
        self.a_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, L, "packet_len")
        self.a_bytes = blocks.repack_bits_bb(1, 8, "packet_len", True, gr.GR_MSB_FIRST)
        self.a_bytes.set_min_output_buffer(70000)
        self.a_bits = blocks.unpack_k_bits_bb(2)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.a_bits, 0), (self.detector_trama, 0))
        self.connect((self.a_bits, 0), (self.marca_preambulo, 0))
        self.connect((self.a_bytes, 0), (self.crc_rx, 0))
        self.connect((self.a_paquetes, 0), (self.crc_tx, 0))
        self.connect((self.acelerador, 0), (self.fase, 0))
        self.connect((self.acelerador, 0), (self.g_canal_esp, 0))
        self.connect((self.acelerador, 0), (self.g_tx_esp, 0))
        self.connect((self.acelerador, 0), (self.g_tx_iq, 0))
        self.connect((self.acelerador, 0), (self.tx_re, 0))
        self.connect((self.alinear, 0), (self.comparar, 0))
        self.connect((self.alinear, 0), (self.rx_bit_float, 0))
        self.connect((self.alinear, 0), (self.rx_bytes_ber, 0))
        self.connect((self.ber_ventana, 0), (self.sonda_ber_ventana, 0))
        self.connect((self.ber_ventana, 0), (self.submuestreo, 0))
        self.connect((self.bits_tx_float, 0), (self.g_bits_tx, 0))
        self.connect((self.bits_tx_unpack, 0), (self.bits_tx_float, 0))
        self.connect((self.cfo, 0), (self.suma_ruido, 0))
        self.connect((self.cfo_real, 0), (self.g_frec, 1))
        self.connect((self.comparar, 0), (self.errores_float, 0))
        self.connect((self.costas, 0), (self.costas_re, 0))
        self.connect((self.costas, 0), (self.decisor, 0))
        self.connect((self.costas, 1), (self.frec_hz, 0))
        self.connect((self.costas, 0), (self.g_sync_const, 1))
        self.connect((self.costas_re, 0), (self.g_histograma, 0))
        self.connect((self.crc_rx, 0), (self.a_pdu, 0))
        self.connect((self.crc_rx, 0), (self.una_de_cien, 0))
        self.connect((self.crc_tx, 0), (self.encabezado, 0))
        self.connect((self.crc_tx, 0), (self.trama, 1))
        self.connect((self.dec_diferencial, 0), (self.mapa_gray, 0))
        self.connect((self.decisor, 0), (self.dec_diferencial, 0))
        self.connect((self.detector_trama, 0), (self.a_bytes, 0))
        self.connect((self.detector_trama, 0), (self.payload_float, 0))
        self.connect((self.encabezado, 0), (self.trama, 0))
        self.connect((self.errores_float, 0), (self.ber_ventana, 0))
        self.connect((self.errores_float, 0), (self.g_bits, 2))
        self.connect((self.fase, 0), (self.cfo, 0))
        self.connect((self.filtro_adaptado, 0), (self.g_mf_t, 0))
        self.connect((self.filtro_adaptado, 0), (self.ojo_interp, 0))
        self.connect((self.filtro_adaptado, 0), (self.sinc_simbolo, 0))
        self.connect((self.frec_hz, 0), (self.g_frec, 0))
        self.connect((self.fuente, 0), (self.a_paquetes, 0))
        self.connect((self.log_ber, 0), (self.g_ber_t, 0))
        self.connect((self.log_teo, 0), (self.g_ber_t, 1))
        self.connect((self.mapa_gray, 0), (self.a_bits, 0))
        self.connect((self.marca_preambulo, 0), (self.alinear, 0))
        self.connect((self.medidor_ber, 0), (self.g_ber_num, 0))
        self.connect((self.medidor_ber, 0), (self.sonda_ber_acum, 0))
        self.connect((self.mf_re, 0), (self.g_ojo, 0))
        self.connect((self.modulador, 0), (self.acelerador, 0))
        self.connect((self.ojo_interp, 0), (self.mf_re, 0))
        self.connect((self.payload_float, 0), (self.g_payload, 0))
        self.connect((self.ref_bit_float, 0), (self.ref_desplazar, 0))
        self.connect((self.ref_bits, 0), (self.ref_saltar_preambulo, 0))
        self.connect((self.ref_bytes_ber, 0), (self.medidor_ber, 1))
        self.connect((self.ref_crc, 0), (self.ref_encabezado, 0))
        self.connect((self.ref_crc, 0), (self.ref_trama, 1))
        self.connect((self.ref_desplazar, 0), (self.g_bits, 1))
        self.connect((self.ref_encabezado, 0), (self.ref_trama, 0))
        self.connect((self.ref_fuente, 0), (self.ref_paquetes, 0))
        self.connect((self.ref_paquetes, 0), (self.ref_crc, 0))
        self.connect((self.ref_saltar_preambulo, 0), (self.comparar, 1))
        self.connect((self.ref_saltar_preambulo, 0), (self.ref_bit_float, 0))
        self.connect((self.ref_saltar_preambulo, 0), (self.ref_bytes_ber, 0))
        self.connect((self.ref_trama, 0), (self.ref_bits, 0))
        self.connect((self.ruido_awgn, 0), (self.suma_ruido, 1))
        self.connect((self.rx_bit_float, 0), (self.g_bits, 0))
        self.connect((self.rx_bytes_ber, 0), (self.medidor_ber, 0))
        self.connect((self.rx_re, 0), (self.g_canal_t, 1))
        self.connect((self.sinc_simbolo, 0), (self.costas, 0))
        self.connect((self.sinc_simbolo, 3), (self.g_periodo, 1))
        self.connect((self.sinc_simbolo, 2), (self.g_periodo, 0))
        self.connect((self.sinc_simbolo, 0), (self.g_sync_const, 0))
        self.connect((self.sinc_simbolo, 1), (self.sinc_err_null, 0))
        self.connect((self.submuestreo, 0), (self.log_ber, 0))
        self.connect((self.suma_ruido, 0), (self.filtro_adaptado, 0))
        self.connect((self.suma_ruido, 0), (self.g_canal_const, 0))
        self.connect((self.suma_ruido, 0), (self.g_canal_esp, 1))
        self.connect((self.suma_ruido, 0), (self.rx_re, 0))
        self.connect((self.trama, 0), (self.bits_tx_unpack, 0))
        self.connect((self.trama, 0), (self.modulador, 0))
        self.connect((self.tx_re, 0), (self.g_canal_t, 0))
        self.connect((self.una_de_cien, 0), (self.archivo_mensajes, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "enlace_4qam_tramas")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_mensaje(self):
        return self.mensaje

    def set_mensaje(self, mensaje):
        self.mensaje = mensaje

    def get_ebn0_db(self):
        return self.ebn0_db

    def set_ebn0_db(self, ebn0_db):
        self.ebn0_db = ebn0_db
        self.set_ruido(math.sqrt(self.sps / (2 * 10**(self.ebn0_db / 10))))
        self.set_p_qpsk(0.5 * math.erfc(math.sqrt(10**(self.ebn0_db / 10))))

    def get_payload(self):
        return self.payload

    def set_payload(self, payload):
        self.payload = payload
        self.set_L(len(self.payload))
        self.fuente.set_data(self.payload, [])
        self.ref_fuente.set_data(self.payload, [])

    def get_p_qpsk(self):
        return self.p_qpsk

    def set_p_qpsk(self, p_qpsk):
        self.p_qpsk = p_qpsk
        self.set_ber_teo(2 * self.p_qpsk * (1 - self.p_qpsk))

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_ruido(math.sqrt(self.sps / (2 * 10**(self.ebn0_db / 10))))
        self.g_bits_tx.set_samp_rate(self.samp_rate/self.sps*2)
        self.filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.sinc_simbolo.set_sps(self.sps)
        self.g_ojo.set_samp_per_symbol((4*self.sps))
        self.g_periodo.set_samp_rate(self.samp_rate/self.sps)
        self.frec_hz.set_k((self.samp_rate / self.sps / (2 * math.pi)))
        self.cfo_real.set_sampling_freq((self.samp_rate/self.sps))
        self.g_frec.set_samp_rate(self.samp_rate/self.sps)
        self.g_payload.set_samp_rate(self.samp_rate/self.sps*2)
        self.log_teo.set_sampling_freq((self.samp_rate/self.sps*2/1000))
        self.g_ber_t.set_samp_rate(self.samp_rate/self.sps*2/1000)
        self.g_bits.set_samp_rate(self.samp_rate/self.sps*2)

    def get_ber_teo(self):
        return self.ber_teo

    def set_ber_teo(self, ber_teo):
        self.ber_teo = ber_teo
        self.set_lbl_teo(self.ber_teo)
        self.set_lbl_ratio((self.ber_rec / self.ber_teo))
        self.log_teo.set_amplitude(math.log10(self.ber_teo))

    def get_ber_rec(self):
        return self.ber_rec

    def set_ber_rec(self, ber_rec):
        self.ber_rec = ber_rec
        self.set_lbl_rec(self.ber_rec)
        self.set_lbl_ratio((self.ber_rec / self.ber_teo))

    def get_ber_acum_log(self):
        return self.ber_acum_log

    def set_ber_acum_log(self, ber_acum_log):
        self.ber_acum_log = ber_acum_log
        self.set_lbl_acum((10**self.ber_acum_log))

    def get_L(self):
        return self.L

    def set_L(self, L):
        self.L = L
        self.set_bits_trama(8*(8 + 4 + self.L + 4))
        self.a_paquetes.set_packet_len(self.L)
        self.a_paquetes.set_packet_len_pmt(self.L)
        self.una_de_cien.set_m(self.L)
        self.una_de_cien.set_n((100*self.L))
        self.ref_paquetes.set_packet_len(self.L)
        self.ref_paquetes.set_packet_len_pmt(self.L)

    def get_ventana(self):
        return self.ventana

    def set_ventana(self, ventana):
        self.ventana = ventana
        self.ber_ventana.set_length_and_scale(self.ventana, (1.0/self.ventana))

    def get_umbral(self):
        return self.umbral

    def set_umbral(self, umbral):
        self.umbral = umbral
        self.marca_preambulo.set_threshold(self.umbral)

    def get_sync_bw(self):
        return self.sync_bw

    def set_sync_bw(self, sync_bw):
        self.sync_bw = sync_bw
        self.sinc_simbolo.set_loop_bandwidth(self.sync_bw)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.acelerador.set_sample_rate(self.samp_rate)
        self.g_bits_tx.set_samp_rate(self.samp_rate/self.sps*2)
        self.g_tx_iq.set_samp_rate(self.samp_rate)
        self.g_tx_esp.set_frequency_range(0, self.samp_rate)
        self.cfo.set_phase_inc((2 * math.pi * self.cfo_hz / self.samp_rate))
        self.g_canal_esp.set_frequency_range(0, self.samp_rate)
        self.g_canal_t.set_samp_rate(self.samp_rate)
        self.filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.g_ojo.set_samp_rate(4*self.samp_rate)
        self.g_mf_t.set_samp_rate(self.samp_rate)
        self.g_periodo.set_samp_rate(self.samp_rate/self.sps)
        self.frec_hz.set_k((self.samp_rate / self.sps / (2 * math.pi)))
        self.cfo_real.set_sampling_freq((self.samp_rate/self.sps))
        self.g_frec.set_samp_rate(self.samp_rate/self.sps)
        self.g_payload.set_samp_rate(self.samp_rate/self.sps*2)
        self.log_teo.set_sampling_freq((self.samp_rate/self.sps*2/1000))
        self.g_ber_t.set_samp_rate(self.samp_rate/self.sps*2/1000)
        self.g_bits.set_samp_rate(self.samp_rate/self.sps*2)

    def get_ruido(self):
        return self.ruido

    def set_ruido(self, ruido):
        self.ruido = ruido
        self.ruido_awgn.set_amplitude(self.ruido)

    def get_qpsk(self):
        return self.qpsk

    def set_qpsk(self, qpsk):
        self.qpsk = qpsk
        self.decisor.set_constellation(self.qpsk)

    def get_lbl_teo(self):
        return self.lbl_teo

    def set_lbl_teo(self, lbl_teo):
        self.lbl_teo = lbl_teo
        Qt.QMetaObject.invokeMethod(self._lbl_teo_label, "setText", Qt.Q_ARG("QString", str(self._lbl_teo_formatter(self.lbl_teo))))

    def get_lbl_rec(self):
        return self.lbl_rec

    def set_lbl_rec(self, lbl_rec):
        self.lbl_rec = lbl_rec
        Qt.QMetaObject.invokeMethod(self._lbl_rec_label, "setText", Qt.Q_ARG("QString", str(self._lbl_rec_formatter(self.lbl_rec))))

    def get_lbl_ratio(self):
        return self.lbl_ratio

    def set_lbl_ratio(self, lbl_ratio):
        self.lbl_ratio = lbl_ratio
        Qt.QMetaObject.invokeMethod(self._lbl_ratio_label, "setText", Qt.Q_ARG("QString", str(self._lbl_ratio_formatter(self.lbl_ratio))))

    def get_lbl_acum(self):
        return self.lbl_acum

    def set_lbl_acum(self, lbl_acum):
        self.lbl_acum = lbl_acum
        Qt.QMetaObject.invokeMethod(self._lbl_acum_label, "setText", Qt.Q_ARG("QString", str(self._lbl_acum_formatter(self.lbl_acum))))

    def get_formato_trama(self):
        return self.formato_trama

    def set_formato_trama(self, formato_trama):
        self.formato_trama = formato_trama
        self.encabezado.set_header_format(self.formato_trama)
        self.ref_encabezado.set_header_format(self.formato_trama)

    def get_fase_deg(self):
        return self.fase_deg

    def set_fase_deg(self, fase_deg):
        self.fase_deg = fase_deg
        self.fase.set_k(cmath.exp(1j * math.radians(self.fase_deg)))

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw
        self.filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_costas_bw(self):
        return self.costas_bw

    def set_costas_bw(self, costas_bw):
        self.costas_bw = costas_bw
        self.costas.set_loop_bandwidth(self.costas_bw)

    def get_cfo_hz(self):
        return self.cfo_hz

    def set_cfo_hz(self, cfo_hz):
        self.cfo_hz = cfo_hz
        self.cfo.set_phase_inc((2 * math.pi * self.cfo_hz / self.samp_rate))
        self.cfo_real.set_amplitude(self.cfo_hz)

    def get_bits_trama(self):
        return self.bits_trama

    def set_bits_trama(self, bits_trama):
        self.bits_trama = bits_trama




def main(top_block_cls=enlace_4qam_tramas, options=None):

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
