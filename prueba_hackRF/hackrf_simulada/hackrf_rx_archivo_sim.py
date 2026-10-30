#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: [SIMULADA] HackRF RX: recepción de un archivo (4-QAM, bloques estándar)
# Author: Juan Gerez
# Description: VERSIÓN SIMULADA de grc_hackrf/hackrf_rx_archivo.grc (la genera hackrf_simulada/generar_grc_simulados.py): en lugar de una HackRF usa emulador_hackrf.py. Recibe con un HackRF los paquetes de hackrf_tx_archivo.grc (FLL, sincronismo, Costas, CRC-32) y guarda los correctos en paquetes_recibidos.bin y datos_recibidos.bin; solo bloques estándar de GNU Radio
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import blocks
import pmt
from gnuradio import digital
from gnuradio import filter
from gnuradio import eng_notation
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import gr, pdu
from gnuradio import network
import math
import sip
import threading
import time



class hackrf_rx_archivo_sim(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "[SIMULADA] HackRF RX: recepción de un archivo (4-QAM, bloques estándar)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("[SIMULADA] HackRF RX: recepción de un archivo (4-QAM, bloques estándar)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "hackrf_rx_archivo_sim")

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
        self.es_n0_db = es_n0_db = 0
        self.samp_rate = samp_rate = 2e6
        self.eb_n0_db = eb_n0_db = es_n0_db - 10 * math.log10(2)
        self.decim = decim = 2
        self.w_fll = w_fll = 0
        self.w_costas = w_costas = 0
        self.sps = sps = 4
        self.samp_rate_rx = samp_rate_rx = samp_rate / decim
        self.p_est = p_est = 0.5 * math.erfc(math.sqrt(10 ** (eb_n0_db / 10)))
        self.items_ok = items_ok = 0
        self.items_detectados = items_detectados = 0
        self.N = N = 200
        self.vga_rx = vga_rx = 20
        self.tramas_detectadas = tramas_detectadas = int(items_detectados) // (8 * (N + 6))
        self.per_est = per_est = 1 - (1 - p_est) ** (8 * (N + 18))
        self.paquetes_ok = paquetes_ok = int(items_ok) // (N + 2)
        self.lna = lna = 16
        self.freq_mhz = freq_mhz = 915
        self.f_offset = f_offset = 400e3
        self.cfo_hz = cfo_hz = -(w_fll * samp_rate_rx + w_costas * samp_rate_rx / sps) / (2 * math.pi)
        self.ber_est = ber_est = 2 * p_est * (1 - p_est)
        self.amp_rx = amp_rx = False
        self.umbral = umbral = 12
        self.taps_canal = taps_canal = firdes.low_pass(1, samp_rate, 300e3, 100e3)
        self.sync_bw = sync_bw = 0.01
        self.qpsk = qpsk = digital.constellation_rect([-0.707-0.707j, 0.707-0.707j, +0.707+0.707j, -0.707+0.707j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.lbl_ppm = lbl_ppm = (cfo_hz / freq_mhz)
        self.lbl_per = lbl_per = per_est
        self.lbl_ok = lbl_ok = paquetes_ok
        self.lbl_mal = lbl_mal = (max(tramas_detectadas - paquetes_ok, 0))
        self.lbl_ebn0 = lbl_ebn0 = eb_n0_db
        self.lbl_detectadas = lbl_detectadas = tramas_detectadas
        self.lbl_cfo = lbl_cfo = cfo_hz
        self.lbl_ber = lbl_ber = ber_est
        self.fll_bw = fll_bw = 0.005
        self.excess_bw = excess_bw = 0.35
        self.dispositivo = dispositivo = ""
        self.costas_bw = costas_bw = 0.01
        self.ajustes_hackrf = ajustes_hackrf = ("equipo=rx frecuencia=%r muestreo=%r lna=%r vga=%r amp=%d" % (float(freq_mhz * 1e6 - f_offset), float(samp_rate), float(lna), float(vga_rx), bool(amp_rx))).encode()

        ##################################################
        # Blocks
        ##################################################

        self._sync_bw_range = qtgui.Range(0.001, 0.1, 0.001, 0.01, 100)
        self._sync_bw_win = qtgui.RangeWidget(self._sync_bw_range, self.set_sync_bw, "BW sinc. de símbolo", "counter", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._sync_bw_win, 1, 2, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.pestanas = Qt.QTabWidget()
        self.pestanas_widget_0 = Qt.QWidget()
        self.pestanas_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_0)
        self.pestanas_grid_layout_0 = Qt.QGridLayout()
        self.pestanas_layout_0.addLayout(self.pestanas_grid_layout_0)
        self.pestanas.addTab(self.pestanas_widget_0, '1. Señal del HackRF')
        self.pestanas_widget_1 = Qt.QWidget()
        self.pestanas_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_1)
        self.pestanas_grid_layout_1 = Qt.QGridLayout()
        self.pestanas_layout_1.addLayout(self.pestanas_grid_layout_1)
        self.pestanas.addTab(self.pestanas_widget_1, '2. Sincronismo (frecuencia, tiempo y fase)')
        self.pestanas_widget_2 = Qt.QWidget()
        self.pestanas_layout_2 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.pestanas_widget_2)
        self.pestanas_grid_layout_2 = Qt.QGridLayout()
        self.pestanas_layout_2.addLayout(self.pestanas_grid_layout_2)
        self.pestanas.addTab(self.pestanas_widget_2, '3. Paquetes recibidos')
        self.top_grid_layout.addWidget(self.pestanas, 3, 0, 1, 5)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.fll_sonda = blocks.probe_signal_f()
        self.estimador_snr = digital.probe_mpsk_snr_est_c(2, 10000, 0.001)
        self.detector_trama = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code,
          umbral, "packet_len")
        self.detector_trama.set_min_output_buffer(600000)
        self.crc = digital.crc32_bb(True, "packet_len", True)
        self.crc.set_min_output_buffer(70000)
        self.costas_sonda = blocks.probe_signal_f()
        def _w_fll_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.fll_sonda.level()
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_w_fll,val))
              except AttributeError:
                self.set_w_fll(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (2))
        _w_fll_thread = threading.Thread(target=_w_fll_probe)
        _w_fll_thread.daemon = True
        _w_fll_thread.start()
        def _w_costas_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.costas_sonda.level()
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_w_costas,val))
              except AttributeError:
                self.set_w_costas(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (2))
        _w_costas_thread = threading.Thread(target=_w_costas_probe)
        _w_costas_thread.daemon = True
        _w_costas_thread.start()
        self._vga_rx_range = qtgui.Range(0, 62, 2, 20, 120)
        self._vga_rx_win = qtgui.RangeWidget(self._vga_rx_range, self.set_vga_rx, "Ganancia VGA [dB]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._vga_rx_win, 0, 3, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.trasladar = filter.freq_xlating_fir_filter_ccf(decim, taps_canal, f_offset, samp_rate)
        self.solo_numero = blocks.keep_m_in_n(gr.sizeof_char, 2, (N + 2), 0)
        self.solo_datos = blocks.keep_m_in_n(gr.sizeof_char, N, (N + 2), 2)
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
        self.sinc_null_3 = blocks.null_sink(gr.sizeof_float*1)
        self.sinc_null_2 = blocks.null_sink(gr.sizeof_float*1)
        self.sinc_null_1 = blocks.null_sink(gr.sizeof_float*1)
        self.separar_bytes = blocks.deinterleave(gr.sizeof_char*1, 1)
        self.por_256 = blocks.multiply_const_ff(256)
        self.ojo_re = blocks.complex_to_real(1)
        self.ojo_interp = filter.rational_resampler_ccc(
                interpolation=4,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.numero_paquete = blocks.add_vff(1)
        self.mapa_gray = digital.map_bb([0, 1, 3, 2])
        self._lna_range = qtgui.Range(0, 40, 8, 16, 120)
        self._lna_win = qtgui.RangeWidget(self._lna_range, self.set_lna, "Ganancia LNA [dB]", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._lna_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_ppm_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.1f' % x:
            self._lbl_ppm_formatter = lambda x: '%.1f' % x
        else:
            self._lbl_ppm_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_ppm_tool_bar.addWidget(Qt.QLabel("Desvío [ppm]: "))
        self._lbl_ppm_label = Qt.QLabel(str(self._lbl_ppm_formatter(self.lbl_ppm)))
        self._lbl_ppm_tool_bar.addWidget(self._lbl_ppm_label)
        self.top_grid_layout.addWidget(self._lbl_ppm_tool_bar, 1, 4, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_per_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.1e' % x if x == x else '-':
            self._lbl_per_formatter = lambda x: '%.1e' % x if x == x else '-'
        else:
            self._lbl_per_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_per_tool_bar.addWidget(Qt.QLabel("PER teórico (Eb/N0 est.): "))
        self._lbl_per_label = Qt.QLabel(str(self._lbl_per_formatter(self.lbl_per)))
        self._lbl_per_tool_bar.addWidget(self._lbl_per_label)
        self.top_grid_layout.addWidget(self._lbl_per_tool_bar, 2, 4, 1, 1)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_ok_tool_bar = Qt.QToolBar(self)

        if None:
            self._lbl_ok_formatter = None
        else:
            self._lbl_ok_formatter = lambda x: str(x)

        self._lbl_ok_tool_bar.addWidget(Qt.QLabel("Con CRC correcto: "))
        self._lbl_ok_label = Qt.QLabel(str(self._lbl_ok_formatter(self.lbl_ok)))
        self._lbl_ok_tool_bar.addWidget(self._lbl_ok_label)
        self.top_grid_layout.addWidget(self._lbl_ok_tool_bar, 2, 0, 1, 1)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_mal_tool_bar = Qt.QToolBar(self)

        if None:
            self._lbl_mal_formatter = None
        else:
            self._lbl_mal_formatter = lambda x: str(x)

        self._lbl_mal_tool_bar.addWidget(Qt.QLabel("Descartadas por CRC: "))
        self._lbl_mal_label = Qt.QLabel(str(self._lbl_mal_formatter(self.lbl_mal)))
        self._lbl_mal_tool_bar.addWidget(self._lbl_mal_label)
        self.top_grid_layout.addWidget(self._lbl_mal_tool_bar, 2, 1, 1, 1)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_ebn0_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.1f dB' % x if x == x else 'sin señal':
            self._lbl_ebn0_formatter = lambda x: '%.1f dB' % x if x == x else 'sin señal'
        else:
            self._lbl_ebn0_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_ebn0_tool_bar.addWidget(Qt.QLabel("Eb/N0 estimado: "))
        self._lbl_ebn0_label = Qt.QLabel(str(self._lbl_ebn0_formatter(self.lbl_ebn0)))
        self._lbl_ebn0_tool_bar.addWidget(self._lbl_ebn0_label)
        self.top_grid_layout.addWidget(self._lbl_ebn0_tool_bar, 2, 2, 1, 1)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_detectadas_tool_bar = Qt.QToolBar(self)

        if None:
            self._lbl_detectadas_formatter = None
        else:
            self._lbl_detectadas_formatter = lambda x: str(x)

        self._lbl_detectadas_tool_bar.addWidget(Qt.QLabel("Tramas detectadas: "))
        self._lbl_detectadas_label = Qt.QLabel(str(self._lbl_detectadas_formatter(self.lbl_detectadas)))
        self._lbl_detectadas_tool_bar.addWidget(self._lbl_detectadas_label)
        self.top_grid_layout.addWidget(self._lbl_detectadas_tool_bar, 0, 4, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_cfo_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.0f Hz' % x:
            self._lbl_cfo_formatter = lambda x: '%.0f Hz' % x
        else:
            self._lbl_cfo_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_cfo_tool_bar.addWidget(Qt.QLabel("Desvío de frecuencia: "))
        self._lbl_cfo_label = Qt.QLabel(str(self._lbl_cfo_formatter(self.lbl_cfo)))
        self._lbl_cfo_tool_bar.addWidget(self._lbl_cfo_label)
        self.top_grid_layout.addWidget(self._lbl_cfo_tool_bar, 1, 3, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._lbl_ber_tool_bar = Qt.QToolBar(self)

        if lambda x: '%.1e' % x if x == x else '-':
            self._lbl_ber_formatter = lambda x: '%.1e' % x if x == x else '-'
        else:
            self._lbl_ber_formatter = lambda x: eng_notation.num_to_str(x)

        self._lbl_ber_tool_bar.addWidget(Qt.QLabel("BER teórico (Eb/N0 est.): "))
        self._lbl_ber_label = Qt.QLabel(str(self._lbl_ber_formatter(self.lbl_ber)))
        self._lbl_ber_tool_bar.addWidget(self._lbl_ber_label)
        self.top_grid_layout.addWidget(self._lbl_ber_tool_bar, 2, 3, 1, 1)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        def _items_ok_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.crc.nitems_written(0)
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_items_ok,val))
              except AttributeError:
                self.set_items_ok(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (2))
        _items_ok_thread = threading.Thread(target=_items_ok_probe)
        _items_ok_thread.daemon = True
        _items_ok_thread.start()
        def _items_detectados_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.detector_trama.nitems_written(0)
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_items_detectados,val))
              except AttributeError:
                self.set_items_detectados(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (2))
        _items_detectados_thread = threading.Thread(target=_items_detectados_probe)
        _items_detectados_thread.daemon = True
        _items_detectados_thread.start()
        self.hackrf_rx_red = network.socket_pdu('UDP_SERVER', '127.0.0.1', '5551', 10000, False)
        self.hackrf_rx_iq = blocks.interleaved_char_to_complex(False,128)
        self.hackrf_rx_bytes = pdu.pdu_to_tagged_stream(gr.types.byte_t, 'trozo_udp')
        self.hackrf_rx = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        self.hackrf_rx.set_single_key("")
        self.g_ojo = qtgui.eye_sink_f(
            1024, #size
            4 * samp_rate_rx, #samp_rate
            1, #number of inputs
            None
        )
        self.g_ojo.set_update_time(0.10)
        self.g_ojo.set_samp_per_symbol((4*sps))
        self.g_ojo.set_y_axis(-2, 2)

        self.g_ojo.set_y_label("Amplitud", "")

        self.g_ojo.enable_tags(False)
        self.g_ojo.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_ojo.enable_autoscale(False)
        self.g_ojo.enable_grid(True)
        self.g_ojo.enable_axis_labels(True)
        self.g_ojo.enable_control_panel(False)


        labels = ['Ojo de I (antes de Costas)', '', '', '', '',
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
        self.g_numero = qtgui.time_sink_f(
            1000, #size
            samp_rate_rx / sps / (8 * (N + 18) / 2), #samp_rate
            "Número de cada paquete recibido con CRC correcto (los saltos son paquetes perdidos)", #name
            1, #number of inputs
            None # parent
        )
        self.g_numero.set_update_time(0.10)
        self.g_numero.set_y_axis(-5, 300)

        self.g_numero.set_y_label('Número de paquete', "")

        self.g_numero.enable_tags(False)
        self.g_numero.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_numero.enable_autoscale(True)
        self.g_numero.enable_grid(True)
        self.g_numero.enable_axis_labels(True)
        self.g_numero.enable_control_panel(False)
        self.g_numero.enable_stem_plot(False)

        self.g_numero.disable_legend()

        labels = ['Paquete', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [0, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [0, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.g_numero.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_numero.set_line_label(i, labels[i])
            self.g_numero.set_line_width(i, widths[i])
            self.g_numero.set_line_color(i, colors[i])
            self.g_numero.set_line_style(i, styles[i])
            self.g_numero.set_line_marker(i, markers[i])
            self.g_numero.set_line_alpha(i, alphas[i])

        self._g_numero_win = sip.wrapinstance(self.g_numero.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_2.addWidget(self._g_numero_win, 0, 0, 1, 3)
        for r in range(0, 1):
            self.pestanas_grid_layout_2.setRowStretch(r, 1)
        for c in range(0, 3):
            self.pestanas_grid_layout_2.setColumnStretch(c, 1)
        self.g_fll = qtgui.time_sink_f(
            2000, #size
            samp_rate_rx, #samp_rate
            "Desvío de frecuencia que estima el FLL [Hz]", #name
            1, #number of inputs
            None # parent
        )
        self.g_fll.set_update_time(0.10)
        self.g_fll.set_y_axis(-60000.0, 60000.0)

        self.g_fll.set_y_label('Hz', "")

        self.g_fll.enable_tags(False)
        self.g_fll.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_fll.enable_autoscale(False)
        self.g_fll.enable_grid(True)
        self.g_fll.enable_axis_labels(True)
        self.g_fll.enable_control_panel(False)
        self.g_fll.enable_stem_plot(False)

        self.g_fll.disable_legend()

        labels = ['FLL', '', '', '', '',
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
                self.g_fll.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_fll.set_line_label(i, labels[i])
            self.g_fll.set_line_width(i, widths[i])
            self.g_fll.set_line_color(i, colors[i])
            self.g_fll.set_line_style(i, styles[i])
            self.g_fll.set_line_marker(i, markers[i])
            self.g_fll.set_line_alpha(i, alphas[i])

        self._g_fll_win = sip.wrapinstance(self.g_fll.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._g_fll_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
        self.g_espectro_crudo = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Espectro del HackRF (señal en +400 kHz; pico del oscilador en 0)", #name
            1,
            None # parent
        )
        self.g_espectro_crudo.set_update_time(0.10)
        self.g_espectro_crudo.set_y_axis((-120), 0)
        self.g_espectro_crudo.set_y_label("Potencia relativa", 'dB')
        self.g_espectro_crudo.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.g_espectro_crudo.enable_autoscale(False)
        self.g_espectro_crudo.enable_grid(True)
        self.g_espectro_crudo.set_fft_average(0.2)
        self.g_espectro_crudo.enable_axis_labels(True)
        self.g_espectro_crudo.enable_control_panel(False)
        self.g_espectro_crudo.set_fft_window_normalized(False)

        self.g_espectro_crudo.disable_legend()


        labels = ['RX', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.g_espectro_crudo.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_espectro_crudo.set_line_label(i, labels[i])
            self.g_espectro_crudo.set_line_width(i, widths[i])
            self.g_espectro_crudo.set_line_color(i, colors[i])
            self.g_espectro_crudo.set_line_alpha(i, alphas[i])

        self._g_espectro_crudo_win = sip.wrapinstance(self.g_espectro_crudo.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_espectro_crudo_win, 0, 0, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_espectro_banda = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate_rx, #bw
            "Espectro trasladado y filtrado (1 M muestras/s)", #name
            1,
            None # parent
        )
        self.g_espectro_banda.set_update_time(0.10)
        self.g_espectro_banda.set_y_axis((-120), 0)
        self.g_espectro_banda.set_y_label("Potencia relativa", 'dB')
        self.g_espectro_banda.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.g_espectro_banda.enable_autoscale(False)
        self.g_espectro_banda.enable_grid(True)
        self.g_espectro_banda.set_fft_average(0.2)
        self.g_espectro_banda.enable_axis_labels(True)
        self.g_espectro_banda.enable_control_panel(False)
        self.g_espectro_banda.set_fft_window_normalized(False)

        self.g_espectro_banda.disable_legend()


        labels = ['Banda base', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.g_espectro_banda.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_espectro_banda.set_line_label(i, labels[i])
            self.g_espectro_banda.set_line_width(i, widths[i])
            self.g_espectro_banda.set_line_color(i, colors[i])
            self.g_espectro_banda.set_line_alpha(i, alphas[i])

        self._g_espectro_banda_win = sip.wrapinstance(self.g_espectro_banda.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_espectro_banda_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(0, 1):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_crudo = qtgui.time_sink_c(
            1000, #size
            samp_rate, #samp_rate
            "Señal cruda del HackRF (si toca ±1, bajar ganancias)", #name
            1, #number of inputs
            None # parent
        )
        self.g_crudo.set_update_time(0.10)
        self.g_crudo.set_y_axis(-1.1, 1.1)

        self.g_crudo.set_y_label('Amplitud', "")

        self.g_crudo.enable_tags(False)
        self.g_crudo.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_crudo.enable_autoscale(False)
        self.g_crudo.enable_grid(True)
        self.g_crudo.enable_axis_labels(True)
        self.g_crudo.enable_control_panel(False)
        self.g_crudo.enable_stem_plot(False)


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
                    self.g_crudo.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.g_crudo.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.g_crudo.set_line_label(i, labels[i])
            self.g_crudo.set_line_width(i, widths[i])
            self.g_crudo.set_line_color(i, colors[i])
            self.g_crudo.set_line_style(i, styles[i])
            self.g_crudo.set_line_marker(i, markers[i])
            self.g_crudo.set_line_alpha(i, alphas[i])

        self._g_crudo_win = sip.wrapinstance(self.g_crudo.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_crudo_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_const = qtgui.const_sink_c(
            1024, #size
            "Constelación antes y después de Costas", #name
            2, #number of inputs
            None # parent
        )
        self.g_const.set_update_time(0.10)
        self.g_const.set_y_axis((-2), 2)
        self.g_const.set_x_axis((-2), 2)
        self.g_const.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.g_const.enable_autoscale(False)
        self.g_const.enable_grid(True)
        self.g_const.enable_axis_labels(True)


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
                self.g_const.set_line_label(i, "Data {0}".format(i))
            else:
                self.g_const.set_line_label(i, labels[i])
            self.g_const.set_line_width(i, widths[i])
            self.g_const.set_line_color(i, colors[i])
            self.g_const.set_line_style(i, styles[i])
            self.g_const.set_line_marker(i, markers[i])
            self.g_const.set_line_alpha(i, alphas[i])

        self._g_const_win = sip.wrapinstance(self.g_const.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_1.addWidget(self._g_const_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_1.setRowStretch(r, 1)
        for c in range(2, 3):
            self.pestanas_grid_layout_1.setColumnStretch(c, 1)
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

        self.pestanas_grid_layout_0.addWidget(self._g_cascada_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(1, 2):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
        self.g_agc = qtgui.time_sink_c(
            400, #size
            samp_rate_rx, #samp_rate
            "Después del AGC (nivel normalizado)", #name
            1, #number of inputs
            None # parent
        )
        self.g_agc.set_update_time(0.10)
        self.g_agc.set_y_axis(-2, 2)

        self.g_agc.set_y_label('Amplitud', "")

        self.g_agc.enable_tags(False)
        self.g_agc.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.g_agc.enable_autoscale(False)
        self.g_agc.enable_grid(True)
        self.g_agc.enable_axis_labels(True)
        self.g_agc.enable_control_panel(False)
        self.g_agc.enable_stem_plot(False)


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
                    self.g_agc.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.g_agc.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.g_agc.set_line_label(i, labels[i])
            self.g_agc.set_line_width(i, widths[i])
            self.g_agc.set_line_color(i, colors[i])
            self.g_agc.set_line_style(i, styles[i])
            self.g_agc.set_line_marker(i, markers[i])
            self.g_agc.set_line_alpha(i, alphas[i])

        self._g_agc_win = sip.wrapinstance(self.g_agc.qwidget(), Qt.QWidget)
        self.pestanas_grid_layout_0.addWidget(self._g_agc_win, 1, 1, 1, 2)
        for r in range(1, 2):
            self.pestanas_grid_layout_0.setRowStretch(r, 1)
        for c in range(1, 3):
            self.pestanas_grid_layout_0.setColumnStretch(c, 1)
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
        self.fll_promedio = blocks.moving_average_ff(100000, (1.0 / 100000), 4000, 1)
        self.fll_null_3 = blocks.null_sink(gr.sizeof_float*1)
        self.fll_null_2 = blocks.null_sink(gr.sizeof_float*1)
        self.fll_hz = blocks.multiply_const_ff((-samp_rate_rx / (2 * math.pi)))
        self._fll_bw_range = qtgui.Range(0.001, 0.1, 0.001, 0.005, 100)
        self._fll_bw_win = qtgui.RangeWidget(self._fll_bw_range, self.set_fll_bw, "BW lazo FLL", "counter", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._fll_bw_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.fll = digital.fll_band_edge_cc(sps, excess_bw, 44, fll_bw)
        self.filtro_adaptado = filter.fft_filter_ccc(1, firdes.root_raised_cosine(1, samp_rate_rx, (samp_rate_rx / sps), excess_bw, (11 * sps)), 1)
        def _es_n0_db_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.estimador_snr.snr()
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_es_n0_db,val))
              except AttributeError:
                self.set_es_n0_db(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (2))
        _es_n0_db_thread = threading.Thread(target=_es_n0_db_probe)
        _es_n0_db_thread.daemon = True
        _es_n0_db_thread.start()
        self.entrada = blocks.copy(gr.sizeof_gr_complex*1)
        self.entrada.set_enabled(True)
        self.decisor = digital.constellation_decoder_cb(qpsk)
        self.dec_diferencial = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.costas_promedio = blocks.moving_average_ff(25000, (1.0 / 25000), 4000, 1)
        self._costas_bw_range = qtgui.Range(0.001, 0.1, 0.001, 0.01, 100)
        self._costas_bw_win = qtgui.RangeWidget(self._costas_bw_range, self.set_costas_bw, "BW lazo de Costas", "counter", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._costas_bw_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.costas = digital.costas_loop_cc(costas_bw, 4, False)
        self.bajo_f = blocks.uchar_to_float()
        self.archivo_paquetes = blocks.file_sink(gr.sizeof_char*1, "paquetes_recibidos.bin", False)
        self.archivo_paquetes.set_unbuffered(True)
        self.archivo_datos = blocks.file_sink(gr.sizeof_char*1, "datos_recibidos.bin", False)
        self.archivo_datos.set_unbuffered(True)
        _amp_rx_check_box = Qt.QCheckBox("Amplificador RX (+11 dB)")
        self._amp_rx_choices = {True: True, False: False}
        self._amp_rx_choices_inv = dict((v,k) for k,v in self._amp_rx_choices.items())
        self._amp_rx_callback = lambda i: Qt.QMetaObject.invokeMethod(_amp_rx_check_box, "setChecked", Qt.Q_ARG("bool", self._amp_rx_choices_inv[i]))
        self._amp_rx_callback(self.amp_rx)
        _amp_rx_check_box.stateChanged.connect(lambda i: self.set_amp_rx(self._amp_rx_choices[bool(i)]))
        self.top_grid_layout.addWidget(_amp_rx_check_box, 0, 1, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.alto_f = blocks.uchar_to_float()
        self.ajustes_red = network.socket_pdu('UDP_CLIENT', '127.0.0.1', '5552', 10000, False)
        self.ajustes_periodicos = blocks.message_strobe(pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(ajustes_hackrf), list(ajustes_hackrf))), 200)
        self.agc = analog.agc2_cc((1e-2), (1e-3), 1.0, 1.0, 65536)
        self.a_bytes = blocks.repack_bits_bb(1, 8, "packet_len", True, gr.GR_MSB_FIRST)
        self.a_bytes.set_min_output_buffer(70000)
        self.a_bits = blocks.unpack_k_bits_bb(2)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.ajustes_periodicos, 'strobe'), (self.ajustes_red, 'pdus'))
        self.msg_connect((self.hackrf_rx_red, 'pdus'), (self.hackrf_rx_bytes, 'pdus'))
        self.connect((self.a_bits, 0), (self.detector_trama, 0))
        self.connect((self.a_bytes, 0), (self.crc, 0))
        self.connect((self.agc, 0), (self.fll, 0))
        self.connect((self.agc, 0), (self.g_agc, 0))
        self.connect((self.alto_f, 0), (self.por_256, 0))
        self.connect((self.bajo_f, 0), (self.numero_paquete, 1))
        self.connect((self.costas, 1), (self.costas_promedio, 0))
        self.connect((self.costas, 0), (self.decisor, 0))
        self.connect((self.costas, 0), (self.estimador_snr, 0))
        self.connect((self.costas, 0), (self.g_const, 1))
        self.connect((self.costas_promedio, 0), (self.costas_sonda, 0))
        self.connect((self.crc, 0), (self.archivo_paquetes, 0))
        self.connect((self.crc, 0), (self.solo_datos, 0))
        self.connect((self.crc, 0), (self.solo_numero, 0))
        self.connect((self.dec_diferencial, 0), (self.mapa_gray, 0))
        self.connect((self.decisor, 0), (self.dec_diferencial, 0))
        self.connect((self.detector_trama, 0), (self.a_bytes, 0))
        self.connect((self.entrada, 0), (self.g_cascada, 0))
        self.connect((self.entrada, 0), (self.g_crudo, 0))
        self.connect((self.entrada, 0), (self.g_espectro_crudo, 0))
        self.connect((self.entrada, 0), (self.trasladar, 0))
        self.connect((self.filtro_adaptado, 0), (self.ojo_interp, 0))
        self.connect((self.filtro_adaptado, 0), (self.sinc_simbolo, 0))
        self.connect((self.fll, 0), (self.filtro_adaptado, 0))
        self.connect((self.fll, 1), (self.fll_hz, 0))
        self.connect((self.fll, 2), (self.fll_null_2, 0))
        self.connect((self.fll, 3), (self.fll_null_3, 0))
        self.connect((self.fll, 1), (self.fll_promedio, 0))
        self.connect((self.fll_hz, 0), (self.g_fll, 0))
        self.connect((self.fll_promedio, 0), (self.fll_sonda, 0))
        self.connect((self.hackrf_rx, 0), (self.entrada, 0))
        self.connect((self.hackrf_rx_bytes, 0), (self.hackrf_rx_iq, 0))
        self.connect((self.hackrf_rx_iq, 0), (self.hackrf_rx, 0))
        self.connect((self.mapa_gray, 0), (self.a_bits, 0))
        self.connect((self.numero_paquete, 0), (self.g_numero, 0))
        self.connect((self.ojo_interp, 0), (self.ojo_re, 0))
        self.connect((self.ojo_re, 0), (self.g_ojo, 0))
        self.connect((self.por_256, 0), (self.numero_paquete, 0))
        self.connect((self.separar_bytes, 0), (self.alto_f, 0))
        self.connect((self.separar_bytes, 1), (self.bajo_f, 0))
        self.connect((self.sinc_simbolo, 0), (self.costas, 0))
        self.connect((self.sinc_simbolo, 0), (self.g_const, 0))
        self.connect((self.sinc_simbolo, 1), (self.sinc_null_1, 0))
        self.connect((self.sinc_simbolo, 2), (self.sinc_null_2, 0))
        self.connect((self.sinc_simbolo, 3), (self.sinc_null_3, 0))
        self.connect((self.solo_datos, 0), (self.archivo_datos, 0))
        self.connect((self.solo_numero, 0), (self.separar_bytes, 0))
        self.connect((self.trasladar, 0), (self.agc, 0))
        self.connect((self.trasladar, 0), (self.g_espectro_banda, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "hackrf_rx_archivo_sim")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_es_n0_db(self):
        return self.es_n0_db

    def set_es_n0_db(self, es_n0_db):
        self.es_n0_db = es_n0_db
        self.set_eb_n0_db(self.es_n0_db - 10 * math.log10(2))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_ajustes_hackrf(("equipo=rx frecuencia=%r muestreo=%r lna=%r vga=%r amp=%d" % (float(self.freq_mhz * 1e6 - self.f_offset), float(self.samp_rate), float(self.lna), float(self.vga_rx), bool(self.amp_rx))).encode())
        self.set_samp_rate_rx(self.samp_rate / self.decim)
        self.set_taps_canal(firdes.low_pass(1, self.samp_rate, 300e3, 100e3))
        self.g_cascada.set_frequency_range(0, self.samp_rate)
        self.g_crudo.set_samp_rate(self.samp_rate)
        self.g_espectro_crudo.set_frequency_range(0, self.samp_rate)

    def get_eb_n0_db(self):
        return self.eb_n0_db

    def set_eb_n0_db(self, eb_n0_db):
        self.eb_n0_db = eb_n0_db
        self.set_lbl_ebn0(self.eb_n0_db)
        self.set_p_est(0.5 * math.erfc(math.sqrt(10 ** (self.eb_n0_db / 10))))

    def get_decim(self):
        return self.decim

    def set_decim(self, decim):
        self.decim = decim
        self.set_samp_rate_rx(self.samp_rate / self.decim)

    def get_w_fll(self):
        return self.w_fll

    def set_w_fll(self, w_fll):
        self.w_fll = w_fll
        self.set_cfo_hz(-(self.w_fll * self.samp_rate_rx + self.w_costas * self.samp_rate_rx / self.sps) / (2 * math.pi))

    def get_w_costas(self):
        return self.w_costas

    def set_w_costas(self, w_costas):
        self.w_costas = w_costas
        self.set_cfo_hz(-(self.w_fll * self.samp_rate_rx + self.w_costas * self.samp_rate_rx / self.sps) / (2 * math.pi))

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_cfo_hz(-(self.w_fll * self.samp_rate_rx + self.w_costas * self.samp_rate_rx / self.sps) / (2 * math.pi))
        self.filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate_rx, (self.samp_rate_rx / self.sps), self.excess_bw, (11 * self.sps)))
        self.g_numero.set_samp_rate(self.samp_rate_rx / self.sps / (8 * (self.N + 18) / 2))
        self.g_ojo.set_samp_per_symbol((4*self.sps))
        self.sinc_simbolo.set_sps(self.sps)

    def get_samp_rate_rx(self):
        return self.samp_rate_rx

    def set_samp_rate_rx(self, samp_rate_rx):
        self.samp_rate_rx = samp_rate_rx
        self.set_cfo_hz(-(self.w_fll * self.samp_rate_rx + self.w_costas * self.samp_rate_rx / self.sps) / (2 * math.pi))
        self.filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate_rx, (self.samp_rate_rx / self.sps), self.excess_bw, (11 * self.sps)))
        self.fll_hz.set_k((-self.samp_rate_rx / (2 * math.pi)))
        self.g_agc.set_samp_rate(self.samp_rate_rx)
        self.g_espectro_banda.set_frequency_range(0, self.samp_rate_rx)
        self.g_fll.set_samp_rate(self.samp_rate_rx)
        self.g_numero.set_samp_rate(self.samp_rate_rx / self.sps / (8 * (self.N + 18) / 2))
        self.g_ojo.set_samp_rate(4 * self.samp_rate_rx)

    def get_p_est(self):
        return self.p_est

    def set_p_est(self, p_est):
        self.p_est = p_est
        self.set_ber_est(2 * self.p_est * (1 - self.p_est))
        self.set_per_est(1 - (1 - self.p_est) ** (8 * (self.N + 18)))

    def get_items_ok(self):
        return self.items_ok

    def set_items_ok(self, items_ok):
        self.items_ok = items_ok
        self.set_paquetes_ok(int(self.items_ok) // (self.N + 2))

    def get_items_detectados(self):
        return self.items_detectados

    def set_items_detectados(self, items_detectados):
        self.items_detectados = items_detectados
        self.set_tramas_detectadas(int(self.items_detectados) // (8 * (self.N + 6)))

    def get_N(self):
        return self.N

    def set_N(self, N):
        self.N = N
        self.set_paquetes_ok(int(self.items_ok) // (self.N + 2))
        self.set_per_est(1 - (1 - self.p_est) ** (8 * (self.N + 18)))
        self.set_tramas_detectadas(int(self.items_detectados) // (8 * (self.N + 6)))
        self.g_numero.set_samp_rate(self.samp_rate_rx / self.sps / (8 * (self.N + 18) / 2))
        self.solo_datos.set_m(self.N)
        self.solo_datos.set_n((self.N + 2))
        self.solo_numero.set_n((self.N + 2))

    def get_vga_rx(self):
        return self.vga_rx

    def set_vga_rx(self, vga_rx):
        self.vga_rx = vga_rx
        self.set_ajustes_hackrf(("equipo=rx frecuencia=%r muestreo=%r lna=%r vga=%r amp=%d" % (float(self.freq_mhz * 1e6 - self.f_offset), float(self.samp_rate), float(self.lna), float(self.vga_rx), bool(self.amp_rx))).encode())

    def get_tramas_detectadas(self):
        return self.tramas_detectadas

    def set_tramas_detectadas(self, tramas_detectadas):
        self.tramas_detectadas = tramas_detectadas
        self.set_lbl_detectadas(self.tramas_detectadas)
        self.set_lbl_mal((max(self.tramas_detectadas - self.paquetes_ok, 0)))

    def get_per_est(self):
        return self.per_est

    def set_per_est(self, per_est):
        self.per_est = per_est
        self.set_lbl_per(self.per_est)

    def get_paquetes_ok(self):
        return self.paquetes_ok

    def set_paquetes_ok(self, paquetes_ok):
        self.paquetes_ok = paquetes_ok
        self.set_lbl_mal((max(self.tramas_detectadas - self.paquetes_ok, 0)))
        self.set_lbl_ok(self.paquetes_ok)

    def get_lna(self):
        return self.lna

    def set_lna(self, lna):
        self.lna = lna
        self.set_ajustes_hackrf(("equipo=rx frecuencia=%r muestreo=%r lna=%r vga=%r amp=%d" % (float(self.freq_mhz * 1e6 - self.f_offset), float(self.samp_rate), float(self.lna), float(self.vga_rx), bool(self.amp_rx))).encode())

    def get_freq_mhz(self):
        return self.freq_mhz

    def set_freq_mhz(self, freq_mhz):
        self.freq_mhz = freq_mhz
        self.set_ajustes_hackrf(("equipo=rx frecuencia=%r muestreo=%r lna=%r vga=%r amp=%d" % (float(self.freq_mhz * 1e6 - self.f_offset), float(self.samp_rate), float(self.lna), float(self.vga_rx), bool(self.amp_rx))).encode())
        Qt.QMetaObject.invokeMethod(self._freq_mhz_line_edit, "setText", Qt.Q_ARG("QString", eng_notation.num_to_str(self.freq_mhz)))
        self.set_lbl_ppm((self.cfo_hz / self.freq_mhz))

    def get_f_offset(self):
        return self.f_offset

    def set_f_offset(self, f_offset):
        self.f_offset = f_offset
        self.set_ajustes_hackrf(("equipo=rx frecuencia=%r muestreo=%r lna=%r vga=%r amp=%d" % (float(self.freq_mhz * 1e6 - self.f_offset), float(self.samp_rate), float(self.lna), float(self.vga_rx), bool(self.amp_rx))).encode())
        self.trasladar.set_center_freq(self.f_offset)

    def get_cfo_hz(self):
        return self.cfo_hz

    def set_cfo_hz(self, cfo_hz):
        self.cfo_hz = cfo_hz
        self.set_lbl_cfo(self.cfo_hz)
        self.set_lbl_ppm((self.cfo_hz / self.freq_mhz))

    def get_ber_est(self):
        return self.ber_est

    def set_ber_est(self, ber_est):
        self.ber_est = ber_est
        self.set_lbl_ber(self.ber_est)

    def get_amp_rx(self):
        return self.amp_rx

    def set_amp_rx(self, amp_rx):
        self.amp_rx = amp_rx
        self.set_ajustes_hackrf(("equipo=rx frecuencia=%r muestreo=%r lna=%r vga=%r amp=%d" % (float(self.freq_mhz * 1e6 - self.f_offset), float(self.samp_rate), float(self.lna), float(self.vga_rx), bool(self.amp_rx))).encode())
        self._amp_rx_callback(self.amp_rx)

    def get_umbral(self):
        return self.umbral

    def set_umbral(self, umbral):
        self.umbral = umbral

    def get_taps_canal(self):
        return self.taps_canal

    def set_taps_canal(self, taps_canal):
        self.taps_canal = taps_canal
        self.trasladar.set_taps(self.taps_canal)

    def get_sync_bw(self):
        return self.sync_bw

    def set_sync_bw(self, sync_bw):
        self.sync_bw = sync_bw
        self.sinc_simbolo.set_loop_bandwidth(self.sync_bw)

    def get_qpsk(self):
        return self.qpsk

    def set_qpsk(self, qpsk):
        self.qpsk = qpsk
        self.decisor.set_constellation(self.qpsk)

    def get_lbl_ppm(self):
        return self.lbl_ppm

    def set_lbl_ppm(self, lbl_ppm):
        self.lbl_ppm = lbl_ppm
        Qt.QMetaObject.invokeMethod(self._lbl_ppm_label, "setText", Qt.Q_ARG("QString", str(self._lbl_ppm_formatter(self.lbl_ppm))))

    def get_lbl_per(self):
        return self.lbl_per

    def set_lbl_per(self, lbl_per):
        self.lbl_per = lbl_per
        Qt.QMetaObject.invokeMethod(self._lbl_per_label, "setText", Qt.Q_ARG("QString", str(self._lbl_per_formatter(self.lbl_per))))

    def get_lbl_ok(self):
        return self.lbl_ok

    def set_lbl_ok(self, lbl_ok):
        self.lbl_ok = lbl_ok
        Qt.QMetaObject.invokeMethod(self._lbl_ok_label, "setText", Qt.Q_ARG("QString", str(self._lbl_ok_formatter(self.lbl_ok))))

    def get_lbl_mal(self):
        return self.lbl_mal

    def set_lbl_mal(self, lbl_mal):
        self.lbl_mal = lbl_mal
        Qt.QMetaObject.invokeMethod(self._lbl_mal_label, "setText", Qt.Q_ARG("QString", str(self._lbl_mal_formatter(self.lbl_mal))))

    def get_lbl_ebn0(self):
        return self.lbl_ebn0

    def set_lbl_ebn0(self, lbl_ebn0):
        self.lbl_ebn0 = lbl_ebn0
        Qt.QMetaObject.invokeMethod(self._lbl_ebn0_label, "setText", Qt.Q_ARG("QString", str(self._lbl_ebn0_formatter(self.lbl_ebn0))))

    def get_lbl_detectadas(self):
        return self.lbl_detectadas

    def set_lbl_detectadas(self, lbl_detectadas):
        self.lbl_detectadas = lbl_detectadas
        Qt.QMetaObject.invokeMethod(self._lbl_detectadas_label, "setText", Qt.Q_ARG("QString", str(self._lbl_detectadas_formatter(self.lbl_detectadas))))

    def get_lbl_cfo(self):
        return self.lbl_cfo

    def set_lbl_cfo(self, lbl_cfo):
        self.lbl_cfo = lbl_cfo
        Qt.QMetaObject.invokeMethod(self._lbl_cfo_label, "setText", Qt.Q_ARG("QString", str(self._lbl_cfo_formatter(self.lbl_cfo))))

    def get_lbl_ber(self):
        return self.lbl_ber

    def set_lbl_ber(self, lbl_ber):
        self.lbl_ber = lbl_ber
        Qt.QMetaObject.invokeMethod(self._lbl_ber_label, "setText", Qt.Q_ARG("QString", str(self._lbl_ber_formatter(self.lbl_ber))))

    def get_fll_bw(self):
        return self.fll_bw

    def set_fll_bw(self, fll_bw):
        self.fll_bw = fll_bw
        self.fll.set_loop_bandwidth(self.fll_bw)

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw
        self.filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate_rx, (self.samp_rate_rx / self.sps), self.excess_bw, (11 * self.sps)))

    def get_dispositivo(self):
        return self.dispositivo

    def set_dispositivo(self, dispositivo):
        self.dispositivo = dispositivo

    def get_costas_bw(self):
        return self.costas_bw

    def set_costas_bw(self, costas_bw):
        self.costas_bw = costas_bw
        self.costas.set_loop_bandwidth(self.costas_bw)

    def get_ajustes_hackrf(self):
        return self.ajustes_hackrf

    def set_ajustes_hackrf(self, ajustes_hackrf):
        self.ajustes_hackrf = ajustes_hackrf
        self.ajustes_periodicos.set_msg(pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(self.ajustes_hackrf), list(self.ajustes_hackrf))))




def main(top_block_cls=hackrf_rx_archivo_sim, options=None):

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
