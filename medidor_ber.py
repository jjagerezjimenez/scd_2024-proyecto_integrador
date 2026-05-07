#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: medidor_ber
# Author: Juan Gerez
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import blocks
import numpy
from gnuradio import channels
from gnuradio.filter import firdes
from gnuradio import digital
from gnuradio import filter
from gnuradio import fec
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



class medidor_ber(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "medidor_ber", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("medidor_ber")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "medidor_ber")

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
        self.samp_rate = samp_rate = 500000
        self.qpsk = qpsk = digital.constellation_rect([-0.707-0.707j, 0.707-0.707j, +0.707+0.707j, -0.707+0.707j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.phase_bw = phase_bw = 0.0628
        self.noise_volt = noise_volt = 0
        self.freq_offset = freq_offset = 0
        self.excess_bw = excess_bw = 0.35
        self.epsilon = epsilon = 1
        self.delay = delay = 52

        ##################################################
        # Blocks
        ##################################################

        self._noise_volt_range = qtgui.Range(0, 1, 0.01, 0, 200)
        self._noise_volt_win = qtgui.RangeWidget(self._noise_volt_range, self.set_noise_volt, "Channel: Noise Voltage", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._noise_volt_win, 0, 0, 1, 10)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 10):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._freq_offset_range = qtgui.Range(-0.1, 0.1, 0.001, 0, 200)
        self._freq_offset_win = qtgui.RangeWidget(self._freq_offset_range, self.set_freq_offset, "Channel: Frequency Offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._freq_offset_win, 1, 0, 1, 10)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 10):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._epsilon_range = qtgui.Range(0.999, 1.001, 0.0001, 1, 200)
        self._epsilon_win = qtgui.RangeWidget(self._epsilon_range, self.set_epsilon, "Channel: Timing Offset", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._epsilon_win, 0, 10, 1, 10)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(10, 20):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._delay_range = qtgui.Range(0, 1000, 1, 52, 200)
        self._delay_win = qtgui.RangeWidget(self._delay_range, self.set_delay, "Delay", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._delay_win, 1, 10, 1, 10)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(10, 20):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_time_sink_x_0 = qtgui.time_sink_f(
            100, #size
            1, #samp_rate
            'Demodulated Bitstream', #name
            2, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0.set_update_time(0.10)
        self.qtgui_time_sink_x_0.set_y_axis(-0.5, 1.5)

        self.qtgui_time_sink_x_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0.enable_tags(True)
        self.qtgui_time_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0.enable_grid(False)
        self.qtgui_time_sink_x_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0.enable_stem_plot(False)


        labels = ['Recovered Data', 'Original Data', '', '', '',
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
                self.qtgui_time_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_time_sink_x_0_win, 2, 10, 10, 10)
        for r in range(2, 12):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(10, 20):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_number_sink_0 = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.qtgui_number_sink_0.set_update_time(0.10)
        self.qtgui_number_sink_0.set_title("Tasa de Error (Log10 BER)")

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        units = ['', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.qtgui_number_sink_0.set_min(i, -7)
            self.qtgui_number_sink_0.set_max(i, 0)
            self.qtgui_number_sink_0.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.qtgui_number_sink_0.set_label(i, "Data {0}".format(i))
            else:
                self.qtgui_number_sink_0.set_label(i, labels[i])
            self.qtgui_number_sink_0.set_unit(i, units[i])
            self.qtgui_number_sink_0.set_factor(i, factor[i])

        self.qtgui_number_sink_0.enable_autoscale(False)
        self._qtgui_number_sink_0_win = sip.wrapinstance(self.qtgui_number_sink_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_number_sink_0_win)
        self.qtgui_freq_sink_x_0 = qtgui.freq_sink_c(
            2048, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            'Transmitted & Received Spectrum', #name
            2,
            None # parent
        )
        self.qtgui_freq_sink_x_0.set_update_time(0.10)
        self.qtgui_freq_sink_x_0.set_y_axis((-140), (-10))
        self.qtgui_freq_sink_x_0.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_0.enable_autoscale(False)
        self.qtgui_freq_sink_x_0.enable_grid(False)
        self.qtgui_freq_sink_x_0.set_fft_average(1.0)
        self.qtgui_freq_sink_x_0.enable_axis_labels(True)
        self.qtgui_freq_sink_x_0.enable_control_panel(False)
        self.qtgui_freq_sink_x_0.set_fft_window_normalized(False)



        labels = ['Transmitted & Propagated', 'Received & Filtered', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(2):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_0_win = sip.wrapinstance(self.qtgui_freq_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_freq_sink_x_0_win, 12, 0, 10, 20)
        for r in range(12, 22):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 20):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_const_sink_x_0 = qtgui.const_sink_c(
            1024, #size
            'Synced Constellation', #name
            2, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0.set_y_axis((-1.5), 1.5)
        self.qtgui_const_sink_x_0.set_x_axis((-1.5), 1.5)
        self.qtgui_const_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0.enable_grid(True)
        self.qtgui_const_sink_x_0.enable_axis_labels(True)


        labels = ['Synced Only', 'Synced & Phase-Locked', '', '', '',
            '', '', '', '', '']
        widths = [1, 2, 2, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "red", "red", "red",
            "red", "red", "red", "red", "red"]
        styles = [0, 0, 1, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, -1, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1, 0.3, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(2):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_0_win = sip.wrapinstance(self.qtgui_const_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_const_sink_x_0_win, 2, 0, 10, 10)
        for r in range(2, 12):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 10):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.filter_fft_rrc_filter_0 = filter.fft_filter_ccc(1, firdes.root_raised_cosine(1, samp_rate, (samp_rate/sps), excess_bw, (11*sps)), 1)
        self.fec_ber_bf_0 = fec.ber_bf(False, 100, -7.0)
        self.digital_symbol_sync_xx_0 = digital.symbol_sync_cc(
            digital.TED_SIGNAL_TIMES_SLOPE_ML,
            sps,
            0.045,
            1.0,
            1.0,
            1.5,
            1,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.digital_map_bb_0 = digital.map_bb([0,1,3,2])
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(phase_bw, 4, False)
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=qpsk,
            differential=True,
            samples_per_symbol=sps,
            pre_diff_code=True,
            excess_bw=excess_bw,
            verbose=False,
            log=False,
            truncate=False)
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(qpsk)
        self.channels_channel_model_0 = channels.channel_model(
            noise_voltage=noise_volt,
            frequency_offset=freq_offset,
            epsilon=epsilon,
            taps=[1],
            noise_seed=0,
            block_tags=False)
        self.blocks_unpack_k_bits_bb_0_0 = blocks.unpack_k_bits_bb(8)
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(2)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_delay_1 = blocks.delay(gr.sizeof_char*1, int(delay))
        self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, int(delay))
        self.blocks_char_to_float_0_0_0 = blocks.char_to_float(1, 1)
        self.blocks_char_to_float_0_0 = blocks.char_to_float(1, 1)
        self.analog_random_source_x_0 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 256, 30000))), True)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_unpack_k_bits_bb_0_0, 0))
        self.connect((self.analog_random_source_x_0, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.blocks_char_to_float_0_0, 0), (self.qtgui_time_sink_x_0, 0))
        self.connect((self.blocks_char_to_float_0_0_0, 0), (self.blocks_delay_0, 0))
        self.connect((self.blocks_delay_0, 0), (self.qtgui_time_sink_x_0, 1))
        self.connect((self.blocks_delay_1, 0), (self.fec_ber_bf_0, 1))
        self.connect((self.blocks_throttle2_0, 0), (self.channels_channel_model_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.blocks_char_to_float_0_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.fec_ber_bf_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0_0, 0), (self.blocks_char_to_float_0_0_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0_0, 0), (self.blocks_delay_1, 0))
        self.connect((self.channels_channel_model_0, 0), (self.filter_fft_rrc_filter_0, 0))
        self.connect((self.channels_channel_model_0, 0), (self.qtgui_freq_sink_x_0, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.qtgui_const_sink_x_0, 1))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.digital_map_bb_0, 0))
        self.connect((self.digital_map_bb_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))
        self.connect((self.digital_symbol_sync_xx_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.digital_symbol_sync_xx_0, 0), (self.qtgui_const_sink_x_0, 0))
        self.connect((self.fec_ber_bf_0, 0), (self.qtgui_number_sink_0, 0))
        self.connect((self.filter_fft_rrc_filter_0, 0), (self.digital_symbol_sync_xx_0, 0))
        self.connect((self.filter_fft_rrc_filter_0, 0), (self.qtgui_freq_sink_x_0, 1))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "medidor_ber")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.digital_symbol_sync_xx_0.set_sps(self.sps)
        self.filter_fft_rrc_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.filter_fft_rrc_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.qtgui_freq_sink_x_0.set_frequency_range(0, self.samp_rate)

    def get_qpsk(self):
        return self.qpsk

    def set_qpsk(self, qpsk):
        self.qpsk = qpsk
        self.digital_constellation_decoder_cb_0.set_constellation(self.qpsk)

    def get_phase_bw(self):
        return self.phase_bw

    def set_phase_bw(self, phase_bw):
        self.phase_bw = phase_bw
        self.digital_costas_loop_cc_0.set_loop_bandwidth(self.phase_bw)

    def get_noise_volt(self):
        return self.noise_volt

    def set_noise_volt(self, noise_volt):
        self.noise_volt = noise_volt
        self.channels_channel_model_0.set_noise_voltage(self.noise_volt)

    def get_freq_offset(self):
        return self.freq_offset

    def set_freq_offset(self, freq_offset):
        self.freq_offset = freq_offset
        self.channels_channel_model_0.set_frequency_offset(self.freq_offset)

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw
        self.filter_fft_rrc_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_epsilon(self):
        return self.epsilon

    def set_epsilon(self, epsilon):
        self.epsilon = epsilon
        self.channels_channel_model_0.set_timing_offset(self.epsilon)

    def get_delay(self):
        return self.delay

    def set_delay(self, delay):
        self.delay = delay
        self.blocks_delay_0.set_dly(int(int(self.delay)))
        self.blocks_delay_1.set_dly(int(int(self.delay)))




def main(top_block_cls=medidor_ber, options=None):

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
