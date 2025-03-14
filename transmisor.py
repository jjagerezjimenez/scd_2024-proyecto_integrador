#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: transmisor
# Author: Gerez
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import blocks
import numpy
from gnuradio import channels
from gnuradio.filter import firdes
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import sip
import threading



class transmisor(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "transmisor", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("transmisor")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "transmisor")

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
        self.sps = sps = 4
        self.polyphase_num_filters = polyphase_num_filters = 32
        self.nfiltros = nfiltros = 64
        self.samp_rate = samp_rate = 32000
        self.rrc_polyphase = rrc_polyphase = firdes.root_raised_cosine(sps, sps,1, 0.35, (11*polyphase_num_filters*sps))
        self.rrc_1 = rrc_1 = firdes.root_raised_cosine(nfiltros, nfiltros*sps,1, 0.35, (11*sps*nfiltros))
        self.noise_amp = noise_amp = 0.0
        self.freq_offset = freq_offset = 0.001
        self.excess_bw = excess_bw = 0.35
        self.const = const = digital.constellation_calcdist([-1-1j, -1+1j, 1+1j, 1-1j], [0, 1, 3, 2],
        4, 1, digital.constellation.AMPLITUDE_NORMALIZATION).base()
        self.const.set_npwr(1.0)

        ##################################################
        # Blocks
        ##################################################

        self.root_raised_cosine_filter_0 = filter.fir_filter_ccf(
            1,
            firdes.root_raised_cosine(
                1,
                samp_rate,
                (samp_rate/sps),
                excess_bw,
                (11*sps)))
        self.qtgui_const_sink_x_1_0_0 = qtgui.const_sink_c(
            1024, #size
            "POLY. SYNC.", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_1_0_0.set_update_time(0.10)
        self.qtgui_const_sink_x_1_0_0.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_1_0_0.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_1_0_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_1_0_0.enable_autoscale(False)
        self.qtgui_const_sink_x_1_0_0.enable_grid(False)
        self.qtgui_const_sink_x_1_0_0.enable_axis_labels(True)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_1_0_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_1_0_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_1_0_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_1_0_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_1_0_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_1_0_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_1_0_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_1_0_0_win = sip.wrapinstance(self.qtgui_const_sink_x_1_0_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_const_sink_x_1_0_0_win)
        self.qtgui_const_sink_x_1_0 = qtgui.const_sink_c(
            1024, #size
            "Luego_Costas", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_1_0.set_update_time(0.10)
        self.qtgui_const_sink_x_1_0.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_1_0.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_1_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_1_0.enable_autoscale(False)
        self.qtgui_const_sink_x_1_0.enable_grid(False)
        self.qtgui_const_sink_x_1_0.enable_axis_labels(True)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_1_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_1_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_1_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_1_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_1_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_1_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_1_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_1_0_win = sip.wrapinstance(self.qtgui_const_sink_x_1_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_const_sink_x_1_0_win)
        self.qtgui_const_sink_x_1 = qtgui.const_sink_c(
            1024, #size
            "CANAL", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_1.set_update_time(0.10)
        self.qtgui_const_sink_x_1.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_1.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_1.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_1.enable_autoscale(False)
        self.qtgui_const_sink_x_1.enable_grid(False)
        self.qtgui_const_sink_x_1.enable_axis_labels(True)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_1.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_1.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_1.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_1.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_1.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_1.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_1.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_1_win = sip.wrapinstance(self.qtgui_const_sink_x_1.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_const_sink_x_1_win)
        self.digital_pfb_clock_sync_xxx_0 = digital.pfb_clock_sync_ccf(sps, .01, rrc_1, nfiltros, (nfiltros//2), 1.5, 1)
        self.digital_fll_band_edge_cc_0 = digital.fll_band_edge_cc(sps, .35, (11*sps), .1)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(0.01, 4, False)
        self.digital_constellation_encoder_bc_0 = digital.constellation_encoder_bc(const)
        self.analog_random_source_x_0 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 256, 1024))), True)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_random_source_x_0, 0), (self.digital_constellation_encoder_bc_0, 0))
        self.connect((self.digital_constellation_encoder_bc_0, 0), (self.digital_fll_band_edge_cc_0, 0))
        self.connect((self.digital_constellation_encoder_bc_0, 0), (self.qtgui_const_sink_x_1, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.qtgui_const_sink_x_1_0, 0))
        self.connect((self.digital_fll_band_edge_cc_0, 0), (self.root_raised_cosine_filter_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.qtgui_const_sink_x_1_0_0, 0))
        self.connect((self.root_raised_cosine_filter_0, 0), (self.digital_pfb_clock_sync_xxx_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "transmisor")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_rrc_1(firdes.root_raised_cosine(self.nfiltros, self.nfiltros*self.sps, 1, 0.35, (11*self.sps*self.nfiltros)))
        self.set_rrc_polyphase(firdes.root_raised_cosine(self.sps, self.sps, 1, 0.35, (11*self.polyphase_num_filters*self.sps)))
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_polyphase_num_filters(self):
        return self.polyphase_num_filters

    def set_polyphase_num_filters(self, polyphase_num_filters):
        self.polyphase_num_filters = polyphase_num_filters
        self.set_rrc_polyphase(firdes.root_raised_cosine(self.sps, self.sps, 1, 0.35, (11*self.polyphase_num_filters*self.sps)))

    def get_nfiltros(self):
        return self.nfiltros

    def set_nfiltros(self, nfiltros):
        self.nfiltros = nfiltros
        self.set_rrc_1(firdes.root_raised_cosine(self.nfiltros, self.nfiltros*self.sps, 1, 0.35, (11*self.sps*self.nfiltros)))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_rrc_polyphase(self):
        return self.rrc_polyphase

    def set_rrc_polyphase(self, rrc_polyphase):
        self.rrc_polyphase = rrc_polyphase

    def get_rrc_1(self):
        return self.rrc_1

    def set_rrc_1(self, rrc_1):
        self.rrc_1 = rrc_1
        self.digital_pfb_clock_sync_xxx_0.update_taps(self.rrc_1)

    def get_noise_amp(self):
        return self.noise_amp

    def set_noise_amp(self, noise_amp):
        self.noise_amp = noise_amp
        self.channels_channel_model_0.set_noise_voltage(self.noise_amp)

    def get_freq_offset(self):
        return self.freq_offset

    def set_freq_offset(self, freq_offset):
        self.freq_offset = freq_offset
        self.channels_channel_model_0.set_frequency_offset((self.freq_offset*10))

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_const(self):
        return self.const

    def set_const(self, const):
        self.const = const
        self.digital_constellation_encoder_bc_0.set_constellation(self.const)




def main(top_block_cls=transmisor, options=None):

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
