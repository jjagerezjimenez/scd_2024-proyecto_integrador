#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Symbol Sync Test (Float)
# Author: Andy Walls
# GNU Radio version: 3.10.10.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSlot
from gnuradio import blocks
import numpy
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
import math
import pmt
import sip
import symbol_sync_test_float_epy_block_0_0 as epy_block_0_0  # embedded python block



class symbol_sync_test_float(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Symbol Sync Test (Float)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Symbol Sync Test (Float)")
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

        self.settings = Qt.QSettings("GNU Radio", "symbol_sync_test_float")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Variables
        ##################################################
        self.zeta = zeta = 1.0
        self.omega_n_norm = omega_n_norm = 0.125
        self.ted_gain = ted_gain = 0.28365
        self.omega_d_norm = omega_d_norm = omega_n_norm*math.sqrt((zeta*zeta-1.0) if zeta > 1.0 else (1.0-zeta*zeta))
        self.proportional_gain = proportional_gain = 2.0/ted_gain*math.exp(-zeta*omega_n_norm)*math.sinh(zeta*omega_n_norm)
        self.integral_gain = integral_gain = 2.0/ted_gain*(1.0-math.exp(-zeta*omega_n_norm)*(math.sinh(zeta*omega_n_norm)+(math.cosh(omega_d_norm) if zeta > 1.0 else math.cos(omega_d_norm))))
        self.sps = sps = 7
        self.proportional_gain_label = proportional_gain_label = "%8.6f" % proportional_gain
        self.packet_time_est_tag = packet_time_est_tag = gr.tag_utils.python_to_tag((9, pmt.intern("test"), pmt.from_double(0.0), pmt.intern("packet_vector_source")))
        self.osps = osps = 1
        self.integral_gain_label = integral_gain_label = "%8.6f" % integral_gain
        self.data_src = data_src = (0,0,0,0,1)
        self.baud_rate = baud_rate = 1200.0

        ##################################################
        # Blocks
        ##################################################

        self._zeta_range = qtgui.Range(0.1, 5.0, 0.1, 1.0, 200)
        self._zeta_win = qtgui.RangeWidget(self._zeta_range, self.set_zeta, "Damping Factor", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._zeta_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._ted_gain_range = qtgui.Range(0.05, 5.0, 0.01, 0.28365, 200)
        self._ted_gain_win = qtgui.RangeWidget(self._ted_gain_range, self.set_ted_gain, "Expected TED Gain", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._ted_gain_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._omega_n_norm_range = qtgui.Range(0.0, 2.0*math.pi*0.25, 0.001, 0.125, 200)
        self._omega_n_norm_win = qtgui.RangeWidget(self._omega_n_norm_range, self.set_omega_n_norm, "Normalized Bandwidth", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._omega_n_norm_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        # Create the options list
        self._data_src_options = [(1, 0, 0, 0, 0), (0, 1, 0, 0, 0), (0, 0, 1, 0, 0), (0, 0, 0, 1, 0), (0, 0, 0, 0, 1)]
        # Create the labels list
        self._data_src_labels = ['Random', 'Low freq', 'Dot Pattern', 'Pulse', 'Packets']
        # Create the combo box
        self._data_src_tool_bar = Qt.QToolBar(self)
        self._data_src_tool_bar.addWidget(Qt.QLabel("Data Source" + ": "))
        self._data_src_combo_box = Qt.QComboBox()
        self._data_src_tool_bar.addWidget(self._data_src_combo_box)
        for _label in self._data_src_labels: self._data_src_combo_box.addItem(_label)
        self._data_src_callback = lambda i: Qt.QMetaObject.invokeMethod(self._data_src_combo_box, "setCurrentIndex", Qt.Q_ARG("int", self._data_src_options.index(i)))
        self._data_src_callback(self.data_src)
        self._data_src_combo_box.currentIndexChanged.connect(
            lambda i: self.set_data_src(self._data_src_options[i]))
        # Create the radio buttons
        self.top_grid_layout.addWidget(self._data_src_tool_bar, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.rational_resampler_xxx_0_0 = filter.rational_resampler_fff(
                interpolation=10,
                decimation=21,
                taps=[],
                fractional_bw=0.45)
        self.qtgui_time_sink_x_0_1_0 = qtgui.time_sink_c(
            (1024*3), #size
            baud_rate*sps, #samp_rate
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0_1_0.set_update_time(0.10)
        self.qtgui_time_sink_x_0_1_0.set_y_axis(-1.5, 1.5)

        self.qtgui_time_sink_x_0_1_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0_1_0.enable_tags(True)
        self.qtgui_time_sink_x_0_1_0.set_trigger_mode(qtgui.TRIG_MODE_NORM, qtgui.TRIG_SLOPE_POS, 0.1, 0.01, 0, '')
        self.qtgui_time_sink_x_0_1_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0_1_0.enable_grid(True)
        self.qtgui_time_sink_x_0_1_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0_1_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0_1_0.enable_stem_plot(False)


        labels = ['', '', '', '', 'Baseband',
            'Abs(Corr)', '', '', '', '']
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
                    self.qtgui_time_sink_x_0_1_0.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.qtgui_time_sink_x_0_1_0.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.qtgui_time_sink_x_0_1_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0_1_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0_1_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0_1_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0_1_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0_1_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_1_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0_1_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_time_sink_x_0_1_0_win, 3, 0, 1, 1)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_time_sink_x_0_0_0_0_0_0 = qtgui.time_sink_c(
            (256*osps), #size
            baud_rate*osps, #samp_rate
            'Symbol Synched Output and Debug', #name
            3, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0_0_0_0_0_0.set_update_time(0.1)
        self.qtgui_time_sink_x_0_0_0_0_0_0.set_y_axis(-1.5, sps+2)

        self.qtgui_time_sink_x_0_0_0_0_0_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0_0_0_0_0_0.enable_tags(True)
        self.qtgui_time_sink_x_0_0_0_0_0_0.set_trigger_mode(qtgui.TRIG_MODE_NORM, qtgui.TRIG_SLOPE_POS, 0.1, 0.01, 0, "time_est")
        self.qtgui_time_sink_x_0_0_0_0_0_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0_0_0_0_0_0.enable_grid(False)
        self.qtgui_time_sink_x_0_0_0_0_0_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0_0_0_0_0_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0_0_0_0_0_0.enable_stem_plot(False)


        labels = ['Soft Bits Re', 'Soft Bits Im', 'Error', 'Instantaneous Period', 'Average Period',
            '(unused)', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            0, 1, 0, 1, 1]
        markers = [1, 0, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(6):
            if len(labels[i]) == 0:
                if (i % 2 == 0):
                    self.qtgui_time_sink_x_0_0_0_0_0_0.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.qtgui_time_sink_x_0_0_0_0_0_0.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.qtgui_time_sink_x_0_0_0_0_0_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0_0_0_0_0_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0_0_0_0_0_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0_0_0_0_0_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0_0_0_0_0_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0_0_0_0_0_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_0_0_0_0_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0_0_0_0_0_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_time_sink_x_0_0_0_0_0_0_win, 3, 1, 1, 2)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._proportional_gain_label_tool_bar = Qt.QToolBar(self)

        if None:
            self._proportional_gain_label_formatter = None
        else:
            self._proportional_gain_label_formatter = lambda x: str(x)

        self._proportional_gain_label_tool_bar.addWidget(Qt.QLabel("Proportional Gain"))
        self._proportional_gain_label_label = Qt.QLabel(str(self._proportional_gain_label_formatter(self.proportional_gain_label)))
        self._proportional_gain_label_tool_bar.addWidget(self._proportional_gain_label_label)
        self.top_grid_layout.addWidget(self._proportional_gain_label_tool_bar, 1, 2, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._integral_gain_label_tool_bar = Qt.QToolBar(self)

        if None:
            self._integral_gain_label_formatter = None
        else:
            self._integral_gain_label_formatter = lambda x: str(x)

        self._integral_gain_label_tool_bar.addWidget(Qt.QLabel("Integral Gain"))
        self._integral_gain_label_label = Qt.QLabel(str(self._integral_gain_label_formatter(self.integral_gain_label)))
        self._integral_gain_label_tool_bar.addWidget(self._integral_gain_label_label)
        self.top_grid_layout.addWidget(self._integral_gain_label_tool_bar, 0, 2, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.fir_filter_xxx_0_1_0_0_0_0 = filter.fir_filter_fff(1, [1.0/float(sps)]*sps)
        self.fir_filter_xxx_0_1_0_0_0_0.declare_sample_delay((int((sps-1.0)/2.0)+4))
        self.epy_block_0_0 = epy_block_0_0.ConstMap()
        self.digital_symbol_sync_xx_0 = digital.symbol_sync_cc(
            digital.TED_MUELLER_AND_MULLER,
            sps,
            omega_n_norm,
            zeta,
            ted_gain,
            1.5,
            osps,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.blocks_vector_source_x_0_0_1_0 = blocks.vector_source_f([1,0]*(4*12*0)+[1,1,0,1,0,1,0,1]*12+[1,0,1,1,1,1,1,0,0,1]+[1,1,1,1,0,1,1,0,0,1]+[1,0,1,1,1,1,1,0,0,1]+[0,1,1,1,0,1,1,0,1,0]+[0,0,0,0,0,1,0,1,0,1,1,0,0,1,1,1,0,0,0,0]+[2]*128, True, 1, [packet_time_est_tag])
        self.blocks_vector_source_x_0_0_1 = blocks.vector_source_f([1]+[0]*7, True, 1, [])
        self.blocks_vector_source_x_0_0_0 = blocks.vector_source_f((0,0,0,0,1,1,1,1), True, 1, [])
        self.blocks_vector_source_x_0_0 = blocks.vector_source_f((0, 1, 0, 1, 0, 1, 0, 1), True, 1, [])
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_float*1, (baud_rate*10),True)
        self.blocks_short_to_float_1 = blocks.short_to_float(1, 1)
        self.blocks_repeat_0_0 = blocks.repeat(gr.sizeof_float*1, (sps*2))
        self.blocks_multiply_matrix_xx_0 = blocks.multiply_matrix_ff((data_src,), gr.TPP_ALL_TO_ALL)
        self.blocks_multiply_const_vxx_1 = blocks.multiply_const_cc(0.707+0.707j)
        self.blocks_float_to_complex_3 = blocks.float_to_complex(1)
        self.blocks_float_to_complex_1_0 = blocks.float_to_complex(1)
        self.blocks_float_to_complex_0_0 = blocks.float_to_complex(1)
        self.analog_random_source_x_0 = blocks.vector_source_s(list(map(int, numpy.random.randint(0, 2, 16384))), True)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_short_to_float_1, 0))
        self.connect((self.blocks_float_to_complex_0_0, 0), (self.qtgui_time_sink_x_0_0_0_0_0_0, 1))
        self.connect((self.blocks_float_to_complex_1_0, 0), (self.qtgui_time_sink_x_0_0_0_0_0_0, 2))
        self.connect((self.blocks_float_to_complex_3, 0), (self.blocks_multiply_const_vxx_1, 0))
        self.connect((self.blocks_multiply_const_vxx_1, 0), (self.digital_symbol_sync_xx_0, 0))
        self.connect((self.blocks_multiply_const_vxx_1, 0), (self.qtgui_time_sink_x_0_1_0, 0))
        self.connect((self.blocks_multiply_matrix_xx_0, 0), (self.blocks_throttle_0, 0))
        self.connect((self.blocks_repeat_0_0, 0), (self.rational_resampler_xxx_0_0, 0))
        self.connect((self.blocks_short_to_float_1, 0), (self.blocks_multiply_matrix_xx_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.epy_block_0_0, 0))
        self.connect((self.blocks_vector_source_x_0_0, 0), (self.blocks_multiply_matrix_xx_0, 2))
        self.connect((self.blocks_vector_source_x_0_0_0, 0), (self.blocks_multiply_matrix_xx_0, 1))
        self.connect((self.blocks_vector_source_x_0_0_1, 0), (self.blocks_multiply_matrix_xx_0, 3))
        self.connect((self.blocks_vector_source_x_0_0_1_0, 0), (self.blocks_multiply_matrix_xx_0, 4))
        self.connect((self.digital_symbol_sync_xx_0, 2), (self.blocks_float_to_complex_0_0, 1))
        self.connect((self.digital_symbol_sync_xx_0, 1), (self.blocks_float_to_complex_0_0, 0))
        self.connect((self.digital_symbol_sync_xx_0, 3), (self.blocks_float_to_complex_1_0, 0))
        self.connect((self.digital_symbol_sync_xx_0, 0), (self.qtgui_time_sink_x_0_0_0_0_0_0, 0))
        self.connect((self.epy_block_0_0, 0), (self.blocks_repeat_0_0, 0))
        self.connect((self.fir_filter_xxx_0_1_0_0_0_0, 0), (self.blocks_float_to_complex_3, 0))
        self.connect((self.rational_resampler_xxx_0_0, 0), (self.fir_filter_xxx_0_1_0_0_0_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "symbol_sync_test_float")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_zeta(self):
        return self.zeta

    def set_zeta(self, zeta):
        self.zeta = zeta
        self.set_integral_gain(2.0/self.ted_gain*(1.0-math.exp(-self.zeta*self.omega_n_norm)*(math.sinh(self.zeta*self.omega_n_norm)+(math.cosh(self.omega_d_norm) if self.zeta > 1.0 else math.cos(self.omega_d_norm)))))
        self.set_omega_d_norm(self.omega_n_norm*math.sqrt((self.zeta*self.zeta-1.0) if self.zeta > 1.0 else (1.0-self.zeta*self.zeta)))
        self.set_proportional_gain(2.0/self.ted_gain*math.exp(-self.zeta*self.omega_n_norm)*math.sinh(self.zeta*self.omega_n_norm))
        self.digital_symbol_sync_xx_0.set_damping_factor(self.zeta)

    def get_omega_n_norm(self):
        return self.omega_n_norm

    def set_omega_n_norm(self, omega_n_norm):
        self.omega_n_norm = omega_n_norm
        self.set_integral_gain(2.0/self.ted_gain*(1.0-math.exp(-self.zeta*self.omega_n_norm)*(math.sinh(self.zeta*self.omega_n_norm)+(math.cosh(self.omega_d_norm) if self.zeta > 1.0 else math.cos(self.omega_d_norm)))))
        self.set_omega_d_norm(self.omega_n_norm*math.sqrt((self.zeta*self.zeta-1.0) if self.zeta > 1.0 else (1.0-self.zeta*self.zeta)))
        self.set_proportional_gain(2.0/self.ted_gain*math.exp(-self.zeta*self.omega_n_norm)*math.sinh(self.zeta*self.omega_n_norm))
        self.digital_symbol_sync_xx_0.set_loop_bandwidth(self.omega_n_norm)

    def get_ted_gain(self):
        return self.ted_gain

    def set_ted_gain(self, ted_gain):
        self.ted_gain = ted_gain
        self.set_integral_gain(2.0/self.ted_gain*(1.0-math.exp(-self.zeta*self.omega_n_norm)*(math.sinh(self.zeta*self.omega_n_norm)+(math.cosh(self.omega_d_norm) if self.zeta > 1.0 else math.cos(self.omega_d_norm)))))
        self.set_proportional_gain(2.0/self.ted_gain*math.exp(-self.zeta*self.omega_n_norm)*math.sinh(self.zeta*self.omega_n_norm))
        self.digital_symbol_sync_xx_0.set_ted_gain(self.ted_gain)

    def get_omega_d_norm(self):
        return self.omega_d_norm

    def set_omega_d_norm(self, omega_d_norm):
        self.omega_d_norm = omega_d_norm
        self.set_integral_gain(2.0/self.ted_gain*(1.0-math.exp(-self.zeta*self.omega_n_norm)*(math.sinh(self.zeta*self.omega_n_norm)+(math.cosh(self.omega_d_norm) if self.zeta > 1.0 else math.cos(self.omega_d_norm)))))

    def get_proportional_gain(self):
        return self.proportional_gain

    def set_proportional_gain(self, proportional_gain):
        self.proportional_gain = proportional_gain
        self.set_proportional_gain_label("%8.6f" % self.proportional_gain)

    def get_integral_gain(self):
        return self.integral_gain

    def set_integral_gain(self, integral_gain):
        self.integral_gain = integral_gain
        self.set_integral_gain_label("%8.6f" % self.integral_gain)

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.blocks_repeat_0_0.set_interpolation((self.sps*2))
        self.digital_symbol_sync_xx_0.set_sps(self.sps)
        self.fir_filter_xxx_0_1_0_0_0_0.set_taps([1.0/float(self.sps)]*self.sps)
        self.qtgui_time_sink_x_0_0_0_0_0_0.set_y_axis(-1.5, self.sps+2)
        self.qtgui_time_sink_x_0_1_0.set_samp_rate(self.baud_rate*self.sps)

    def get_proportional_gain_label(self):
        return self.proportional_gain_label

    def set_proportional_gain_label(self, proportional_gain_label):
        self.proportional_gain_label = proportional_gain_label
        Qt.QMetaObject.invokeMethod(self._proportional_gain_label_label, "setText", Qt.Q_ARG("QString", str(self._proportional_gain_label_formatter(self.proportional_gain_label))))

    def get_packet_time_est_tag(self):
        return self.packet_time_est_tag

    def set_packet_time_est_tag(self, packet_time_est_tag):
        self.packet_time_est_tag = packet_time_est_tag
        self.blocks_vector_source_x_0_0_1_0.set_data([1,0]*(4*12*0)+[1,1,0,1,0,1,0,1]*12+[1,0,1,1,1,1,1,0,0,1]+[1,1,1,1,0,1,1,0,0,1]+[1,0,1,1,1,1,1,0,0,1]+[0,1,1,1,0,1,1,0,1,0]+[0,0,0,0,0,1,0,1,0,1,1,0,0,1,1,1,0,0,0,0]+[2]*128, [self.packet_time_est_tag])

    def get_osps(self):
        return self.osps

    def set_osps(self, osps):
        self.osps = osps
        self.qtgui_time_sink_x_0_0_0_0_0_0.set_samp_rate(self.baud_rate*self.osps)

    def get_integral_gain_label(self):
        return self.integral_gain_label

    def set_integral_gain_label(self, integral_gain_label):
        self.integral_gain_label = integral_gain_label
        Qt.QMetaObject.invokeMethod(self._integral_gain_label_label, "setText", Qt.Q_ARG("QString", str(self._integral_gain_label_formatter(self.integral_gain_label))))

    def get_data_src(self):
        return self.data_src

    def set_data_src(self, data_src):
        self.data_src = data_src
        self._data_src_callback(self.data_src)
        self.blocks_multiply_matrix_xx_0.set_A((self.data_src,))

    def get_baud_rate(self):
        return self.baud_rate

    def set_baud_rate(self, baud_rate):
        self.baud_rate = baud_rate
        self.blocks_throttle_0.set_sample_rate((self.baud_rate*10))
        self.qtgui_time_sink_x_0_0_0_0_0_0.set_samp_rate(self.baud_rate*self.osps)
        self.qtgui_time_sink_x_0_1_0.set_samp_rate(self.baud_rate*self.sps)




def main(top_block_cls=symbol_sync_test_float, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

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
