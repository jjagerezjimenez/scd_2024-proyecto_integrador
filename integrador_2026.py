#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: integrador_2026
# Author: Juan Gerez Jimenez
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import blocks
import numpy
from gnuradio import channels
from gnuradio.filter import firdes
from gnuradio import digital
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



class integrador_2026(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "integrador_2026", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("integrador_2026")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "integrador_2026")

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
        self.samp_rate = samp_rate = 32000
        self.qam4 = qam4 = digital.constellation_qpsk().base()
        self.qam4.set_npwr(1.0)
        self.noise_var = noise_var = 0.1

        ##################################################
        # Blocks
        ##################################################

        self._noise_var_range = qtgui.Range(0, 1, 0.05, 0.1, 200)
        self._noise_var_win = qtgui.RangeWidget(self._noise_var_range, self.set_noise_var, "Nivel de Ruido", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._noise_var_win)
        self.qtgui_const_sink_x_0 = qtgui.const_sink_c(
            1024, #size
            "Comparacion 4-QAM", #name
            2, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_0.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0.enable_grid(False)
        self.qtgui_const_sink_x_0.enable_axis_labels(True)


        labels = ['TX (Senal Pura)', 'RX (Canal con Ruido)', '', '', '',
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
        self.top_layout.addWidget(self._qtgui_const_sink_x_0_win)
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=qam4,
            differential=False,
            samples_per_symbol=4,
            pre_diff_code=True,
            excess_bw=0.35,
            verbose=False,
            log=False,
            truncate=False)
        self.channels_channel_model_0 = channels.channel_model(
            noise_voltage=noise_var,
            frequency_offset=0.0,
            epsilon=1.0,
            taps=[1.0],
            noise_seed=0,
            block_tags=False)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_char*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.analog_random_source_x_0 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 256, 1024))), True)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.channels_channel_model_0, 0), (self.qtgui_const_sink_x_0, 1))
        self.connect((self.digital_constellation_modulator_0, 0), (self.channels_channel_model_0, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.qtgui_const_sink_x_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "integrador_2026")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)

    def get_qam4(self):
        return self.qam4

    def set_qam4(self, qam4):
        self.qam4 = qam4

    def get_noise_var(self):
        return self.noise_var

    def set_noise_var(self, noise_var):
        self.noise_var = noise_var
        self.channels_channel_model_0.set_noise_voltage(self.noise_var)




def main(top_block_cls=integrador_2026, options=None):

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
