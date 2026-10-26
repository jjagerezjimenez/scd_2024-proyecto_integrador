#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Medición de BER del enlace half-duplex 4-QAM (sin interfaz)
# Author: Juan Gerez
# Description: El mismo enlace half-duplex de halfduplex_4qam.grc, sin gráficos, para medir BER por línea de comandos
# GNU Radio version: 3.10.12.0

from gnuradio import analog
from gnuradio import blocks
from gnuradio import blocks, gr
from gnuradio import digital
from gnuradio import filter
from gnuradio import fec
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import gr, pdu
import math, cmath
import threading




class halfduplex_4qam_ber(gr.top_block):

    def __init__(self, ebn0_db=6.0, fase_deg=0.0, cfo_hz=0.0, costas_bw=0.005, sync_bw=0.01, muestras=4000000, semilla=1, descartar=100000):
        gr.top_block.__init__(self, "Medición de BER del enlace half-duplex 4-QAM (sin interfaz)", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Parameters
        ##################################################
        self.ebn0_db = ebn0_db
        self.fase_deg = fase_deg
        self.cfo_hz = cfo_hz
        self.costas_bw = costas_bw
        self.sync_bw = sync_bw
        self.muestras = muestras
        self.semilla = semilla
        self.descartar = descartar

        ##################################################
        # Variables
        ##################################################
        self.mensaje_B = mensaje_B = "Hola, soy el nodo B. Respondo en la otra ranura: nunca transmitimos los dos al mismo tiempo!!"
        self.mensaje_A = mensaje_A = "Hola, soy el nodo A. Este mensaje viaja por el canal compartido en mi ranura de tiempo (TDD)."
        self.sps = sps = 4
        self.payload_B = payload_B = list(mensaje_B.encode())
        self.payload_A = payload_A = list(mensaje_A.encode())
        self.umbral = umbral = 12
        self.samp_rate = samp_rate = 500000
        self.ruido = ruido = math.sqrt(sps / (2 * 10**(ebn0_db / 10)))
        self.ranura = ranura = 2048
        self.qpsk = qpsk = digital.constellation_rect([-0.707-0.707j, 0.707-0.707j, +0.707+0.707j, -0.707+0.707j], [0, 1, 3, 2],
        4, 2, 2, 1, 1).base()
        self.guarda = guarda = 256
        self.formato_trama = formato_trama = digital.header_format_default(digital.packet_utils.default_access_code,0, 1)
        self.excess_bw = excess_bw = 0.35
        self.L_B = L_B = len(payload_B)
        self.L_A = L_A = len(payload_A)

        ##################################################
        # Blocks
        ##################################################

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
        self.suma_ruido = blocks.add_vcc(1)
        self.silencio_3 = blocks.null_source(gr.sizeof_gr_complex*1)
        self.silencio_1 = blocks.null_source(gr.sizeof_gr_complex*1)
        self.rxB_sonda_ber = blocks.probe_signal_f()
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
        self.rxB_rx_descartar = blocks.skiphead(gr.sizeof_char*1, descartar)
        self.rxB_rx_bytes = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rxB_ref_trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.rxB_ref_saltar_preambulo = blocks.skiphead(gr.sizeof_char*1, 64)
        self.rxB_ref_fuente = blocks.vector_source_b(payload_A, True, 1, [])
        self.rxB_ref_encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self.rxB_ref_descartar = blocks.skiphead(gr.sizeof_char*1, descartar)
        self.rxB_ref_crc = digital.crc32_bb(False, "packet_len", True)
        self.rxB_ref_bytes = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rxB_ref_bits = blocks.unpack_k_bits_bb(8)
        self.rxB_ref_a_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, L_A, "packet_len")
        self.rxB_mensajes = blocks.message_debug(True, gr.log_levels.info)
        self.rxB_medidor_ber = fec.ber_bf(False, 100, -7.0)
        self.rxB_marca_preambulo = digital.correlate_access_code_tag_bb(digital.packet_utils.default_access_code, umbral, "inicio_trama")
        self.rxB_mapa_gray = digital.map_bb([0, 1, 3, 2])
        self.rxB_filtro_adaptado = filter.fft_filter_ccc(1, firdes.root_raised_cosine(1, samp_rate, (samp_rate/sps), excess_bw, (11*sps)), 1)
        self.rxB_detector_trama = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code,
          umbral, "packet_len")
        self.rxB_detector_trama.set_min_output_buffer(600000)
        self.rxB_decisor = digital.constellation_decoder_cb(qpsk)
        self.rxB_dec_diferencial = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.rxB_crc = digital.crc32_bb(True, "packet_len", True)
        self.rxB_crc.set_min_output_buffer(70000)
        self.rxB_costas = digital.costas_loop_cc(costas_bw, 4, False)
        self.rxB_alinear = blocks.tagged_stream_align(gr.sizeof_char*1, "inicio_trama")
        self.rxB_a_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, "packet_len")
        self.rxB_a_bytes = blocks.repack_bits_bb(1, 8, "packet_len", True, gr.GR_MSB_FIRST)
        self.rxB_a_bytes.set_min_output_buffer(70000)
        self.rxB_a_bits = blocks.unpack_k_bits_bb(2)
        self.rxA_sonda_ber = blocks.probe_signal_f()
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
        self.rxA_rx_descartar = blocks.skiphead(gr.sizeof_char*1, descartar)
        self.rxA_rx_bytes = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rxA_ref_trama = blocks.tagged_stream_mux(gr.sizeof_char*1, "packet_len", 0)
        self.rxA_ref_saltar_preambulo = blocks.skiphead(gr.sizeof_char*1, 64)
        self.rxA_ref_fuente = blocks.vector_source_b(payload_B, True, 1, [])
        self.rxA_ref_encabezado = digital.protocol_formatter_bb(formato_trama, "packet_len")
        self.rxA_ref_descartar = blocks.skiphead(gr.sizeof_char*1, descartar)
        self.rxA_ref_crc = digital.crc32_bb(False, "packet_len", True)
        self.rxA_ref_bytes = blocks.repack_bits_bb(1, 8, "", False, gr.GR_MSB_FIRST)
        self.rxA_ref_bits = blocks.unpack_k_bits_bb(8)
        self.rxA_ref_a_paquetes = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, L_B, "packet_len")
        self.rxA_mensajes = blocks.message_debug(True, gr.log_levels.info)
        self.rxA_medidor_ber = fec.ber_bf(False, 100, -7.0)
        self.rxA_marca_preambulo = digital.correlate_access_code_tag_bb(digital.packet_utils.default_access_code, umbral, "inicio_trama")
        self.rxA_mapa_gray = digital.map_bb([0, 1, 3, 2])
        self.rxA_filtro_adaptado = filter.fft_filter_ccc(1, firdes.root_raised_cosine(1, samp_rate, (samp_rate/sps), excess_bw, (11*sps)), 1)
        self.rxA_detector_trama = digital.correlate_access_code_bb_ts(digital.packet_utils.default_access_code,
          umbral, "packet_len")
        self.rxA_detector_trama.set_min_output_buffer(600000)
        self.rxA_decisor = digital.constellation_decoder_cb(qpsk)
        self.rxA_dec_diferencial = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.rxA_crc = digital.crc32_bb(True, "packet_len", True)
        self.rxA_crc.set_min_output_buffer(70000)
        self.rxA_costas = digital.costas_loop_cc(costas_bw, 4, False)
        self.rxA_alinear = blocks.tagged_stream_align(gr.sizeof_char*1, "inicio_trama")
        self.rxA_a_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, "packet_len")
        self.rxA_a_bytes = blocks.repack_bits_bb(1, 8, "packet_len", True, gr.GR_MSB_FIRST)
        self.rxA_a_bytes.set_min_output_buffer(70000)
        self.rxA_a_bits = blocks.unpack_k_bits_bb(2)
        self.ruido_awgn = analog.noise_source_c(analog.GR_GAUSSIAN, ruido, semilla)
        self.osc_rxB = blocks.rotator_cc((2 * math.pi * cfo_hz / samp_rate), False)
        self.osc_rxA = blocks.rotator_cc((-2 * math.pi * cfo_hz / samp_rate), False)
        self.limite = blocks.head(gr.sizeof_gr_complex*1, muestras)
        self.guarda_3 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.guarda_1 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.fase = blocks.multiply_const_cc(cmath.exp(1j * math.radians(fase_deg)))
        self.conmutador_rx = blocks.stream_demux(gr.sizeof_gr_complex*1, [ranura, guarda, ranura, guarda])


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.rxA_a_pdu, 'pdus'), (self.rxA_mensajes, 'store'))
        self.msg_connect((self.rxB_a_pdu, 'pdus'), (self.rxB_mensajes, 'store'))
        self.connect((self.conmutador_rx, 1), (self.guarda_1, 0))
        self.connect((self.conmutador_rx, 3), (self.guarda_3, 0))
        self.connect((self.conmutador_rx, 2), (self.osc_rxA, 0))
        self.connect((self.conmutador_rx, 0), (self.osc_rxB, 0))
        self.connect((self.fase, 0), (self.suma_ruido, 0))
        self.connect((self.limite, 0), (self.fase, 0))
        self.connect((self.osc_rxA, 0), (self.rxA_filtro_adaptado, 0))
        self.connect((self.osc_rxB, 0), (self.rxB_filtro_adaptado, 0))
        self.connect((self.ruido_awgn, 0), (self.suma_ruido, 1))
        self.connect((self.rxA_a_bits, 0), (self.rxA_detector_trama, 0))
        self.connect((self.rxA_a_bits, 0), (self.rxA_marca_preambulo, 0))
        self.connect((self.rxA_a_bytes, 0), (self.rxA_crc, 0))
        self.connect((self.rxA_alinear, 0), (self.rxA_rx_descartar, 0))
        self.connect((self.rxA_costas, 0), (self.rxA_decisor, 0))
        self.connect((self.rxA_crc, 0), (self.rxA_a_pdu, 0))
        self.connect((self.rxA_dec_diferencial, 0), (self.rxA_mapa_gray, 0))
        self.connect((self.rxA_decisor, 0), (self.rxA_dec_diferencial, 0))
        self.connect((self.rxA_detector_trama, 0), (self.rxA_a_bytes, 0))
        self.connect((self.rxA_filtro_adaptado, 0), (self.rxA_sinc_simbolo, 0))
        self.connect((self.rxA_mapa_gray, 0), (self.rxA_a_bits, 0))
        self.connect((self.rxA_marca_preambulo, 0), (self.rxA_alinear, 0))
        self.connect((self.rxA_medidor_ber, 0), (self.rxA_sonda_ber, 0))
        self.connect((self.rxA_ref_a_paquetes, 0), (self.rxA_ref_crc, 0))
        self.connect((self.rxA_ref_bits, 0), (self.rxA_ref_saltar_preambulo, 0))
        self.connect((self.rxA_ref_bytes, 0), (self.rxA_medidor_ber, 1))
        self.connect((self.rxA_ref_crc, 0), (self.rxA_ref_encabezado, 0))
        self.connect((self.rxA_ref_crc, 0), (self.rxA_ref_trama, 1))
        self.connect((self.rxA_ref_descartar, 0), (self.rxA_ref_bytes, 0))
        self.connect((self.rxA_ref_encabezado, 0), (self.rxA_ref_trama, 0))
        self.connect((self.rxA_ref_fuente, 0), (self.rxA_ref_a_paquetes, 0))
        self.connect((self.rxA_ref_saltar_preambulo, 0), (self.rxA_ref_descartar, 0))
        self.connect((self.rxA_ref_trama, 0), (self.rxA_ref_bits, 0))
        self.connect((self.rxA_rx_bytes, 0), (self.rxA_medidor_ber, 0))
        self.connect((self.rxA_rx_descartar, 0), (self.rxA_rx_bytes, 0))
        self.connect((self.rxA_sinc_simbolo, 0), (self.rxA_costas, 0))
        self.connect((self.rxA_sinc_simbolo, 1), (self.rxA_sinc_null_1, 0))
        self.connect((self.rxA_sinc_simbolo, 2), (self.rxA_sinc_null_2, 0))
        self.connect((self.rxA_sinc_simbolo, 3), (self.rxA_sinc_null_3, 0))
        self.connect((self.rxB_a_bits, 0), (self.rxB_detector_trama, 0))
        self.connect((self.rxB_a_bits, 0), (self.rxB_marca_preambulo, 0))
        self.connect((self.rxB_a_bytes, 0), (self.rxB_crc, 0))
        self.connect((self.rxB_alinear, 0), (self.rxB_rx_descartar, 0))
        self.connect((self.rxB_costas, 0), (self.rxB_decisor, 0))
        self.connect((self.rxB_crc, 0), (self.rxB_a_pdu, 0))
        self.connect((self.rxB_dec_diferencial, 0), (self.rxB_mapa_gray, 0))
        self.connect((self.rxB_decisor, 0), (self.rxB_dec_diferencial, 0))
        self.connect((self.rxB_detector_trama, 0), (self.rxB_a_bytes, 0))
        self.connect((self.rxB_filtro_adaptado, 0), (self.rxB_sinc_simbolo, 0))
        self.connect((self.rxB_mapa_gray, 0), (self.rxB_a_bits, 0))
        self.connect((self.rxB_marca_preambulo, 0), (self.rxB_alinear, 0))
        self.connect((self.rxB_medidor_ber, 0), (self.rxB_sonda_ber, 0))
        self.connect((self.rxB_ref_a_paquetes, 0), (self.rxB_ref_crc, 0))
        self.connect((self.rxB_ref_bits, 0), (self.rxB_ref_saltar_preambulo, 0))
        self.connect((self.rxB_ref_bytes, 0), (self.rxB_medidor_ber, 1))
        self.connect((self.rxB_ref_crc, 0), (self.rxB_ref_encabezado, 0))
        self.connect((self.rxB_ref_crc, 0), (self.rxB_ref_trama, 1))
        self.connect((self.rxB_ref_descartar, 0), (self.rxB_ref_bytes, 0))
        self.connect((self.rxB_ref_encabezado, 0), (self.rxB_ref_trama, 0))
        self.connect((self.rxB_ref_fuente, 0), (self.rxB_ref_a_paquetes, 0))
        self.connect((self.rxB_ref_saltar_preambulo, 0), (self.rxB_ref_descartar, 0))
        self.connect((self.rxB_ref_trama, 0), (self.rxB_ref_bits, 0))
        self.connect((self.rxB_rx_bytes, 0), (self.rxB_medidor_ber, 0))
        self.connect((self.rxB_rx_descartar, 0), (self.rxB_rx_bytes, 0))
        self.connect((self.rxB_sinc_simbolo, 0), (self.rxB_costas, 0))
        self.connect((self.rxB_sinc_simbolo, 1), (self.rxB_sinc_null_1, 0))
        self.connect((self.rxB_sinc_simbolo, 2), (self.rxB_sinc_null_2, 0))
        self.connect((self.rxB_sinc_simbolo, 3), (self.rxB_sinc_null_3, 0))
        self.connect((self.silencio_1, 0), (self.turnos, 1))
        self.connect((self.silencio_3, 0), (self.turnos, 3))
        self.connect((self.suma_ruido, 0), (self.conmutador_rx, 0))
        self.connect((self.turnos, 0), (self.limite, 0))
        self.connect((self.txA_a_paquetes, 0), (self.txA_crc, 0))
        self.connect((self.txA_crc, 0), (self.txA_encabezado, 0))
        self.connect((self.txA_crc, 0), (self.txA_trama, 1))
        self.connect((self.txA_encabezado, 0), (self.txA_trama, 0))
        self.connect((self.txA_fuente, 0), (self.txA_a_paquetes, 0))
        self.connect((self.txA_modulador, 0), (self.turnos, 0))
        self.connect((self.txA_trama, 0), (self.txA_modulador, 0))
        self.connect((self.txB_a_paquetes, 0), (self.txB_crc, 0))
        self.connect((self.txB_crc, 0), (self.txB_encabezado, 0))
        self.connect((self.txB_crc, 0), (self.txB_trama, 1))
        self.connect((self.txB_encabezado, 0), (self.txB_trama, 0))
        self.connect((self.txB_fuente, 0), (self.txB_a_paquetes, 0))
        self.connect((self.txB_modulador, 0), (self.turnos, 2))
        self.connect((self.txB_trama, 0), (self.txB_modulador, 0))


    def get_ebn0_db(self):
        return self.ebn0_db

    def set_ebn0_db(self, ebn0_db):
        self.ebn0_db = ebn0_db
        self.set_ruido(math.sqrt(self.sps / (2 * 10**(self.ebn0_db / 10))))

    def get_fase_deg(self):
        return self.fase_deg

    def set_fase_deg(self, fase_deg):
        self.fase_deg = fase_deg
        self.fase.set_k(cmath.exp(1j * math.radians(self.fase_deg)))

    def get_cfo_hz(self):
        return self.cfo_hz

    def set_cfo_hz(self, cfo_hz):
        self.cfo_hz = cfo_hz
        self.osc_rxB.set_phase_inc((2 * math.pi * self.cfo_hz / self.samp_rate))
        self.osc_rxA.set_phase_inc((-2 * math.pi * self.cfo_hz / self.samp_rate))

    def get_costas_bw(self):
        return self.costas_bw

    def set_costas_bw(self, costas_bw):
        self.costas_bw = costas_bw
        self.rxA_costas.set_loop_bandwidth(self.costas_bw)
        self.rxB_costas.set_loop_bandwidth(self.costas_bw)

    def get_sync_bw(self):
        return self.sync_bw

    def set_sync_bw(self, sync_bw):
        self.sync_bw = sync_bw
        self.rxA_sinc_simbolo.set_loop_bandwidth(self.sync_bw)
        self.rxB_sinc_simbolo.set_loop_bandwidth(self.sync_bw)

    def get_muestras(self):
        return self.muestras

    def set_muestras(self, muestras):
        self.muestras = muestras
        self.limite.set_length(self.muestras)

    def get_semilla(self):
        return self.semilla

    def set_semilla(self, semilla):
        self.semilla = semilla

    def get_descartar(self):
        return self.descartar

    def set_descartar(self, descartar):
        self.descartar = descartar

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
        self.rxA_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxA_sinc_simbolo.set_sps(self.sps)
        self.rxB_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxB_sinc_simbolo.set_sps(self.sps)

    def get_payload_B(self):
        return self.payload_B

    def set_payload_B(self, payload_B):
        self.payload_B = payload_B
        self.set_L_B(len(self.payload_B))
        self.txB_fuente.set_data(self.payload_B, [])
        self.rxA_ref_fuente.set_data(self.payload_B, [])

    def get_payload_A(self):
        return self.payload_A

    def set_payload_A(self, payload_A):
        self.payload_A = payload_A
        self.set_L_A(len(self.payload_A))
        self.txA_fuente.set_data(self.payload_A, [])
        self.rxB_ref_fuente.set_data(self.payload_A, [])

    def get_umbral(self):
        return self.umbral

    def set_umbral(self, umbral):
        self.umbral = umbral
        self.rxA_marca_preambulo.set_threshold(self.umbral)
        self.rxB_marca_preambulo.set_threshold(self.umbral)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.osc_rxB.set_phase_inc((2 * math.pi * self.cfo_hz / self.samp_rate))
        self.osc_rxA.set_phase_inc((-2 * math.pi * self.cfo_hz / self.samp_rate))
        self.rxA_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxB_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_ruido(self):
        return self.ruido

    def set_ruido(self, ruido):
        self.ruido = ruido
        self.ruido_awgn.set_amplitude(self.ruido)

    def get_ranura(self):
        return self.ranura

    def set_ranura(self, ranura):
        self.ranura = ranura

    def get_qpsk(self):
        return self.qpsk

    def set_qpsk(self, qpsk):
        self.qpsk = qpsk
        self.rxA_decisor.set_constellation(self.qpsk)
        self.rxB_decisor.set_constellation(self.qpsk)

    def get_guarda(self):
        return self.guarda

    def set_guarda(self, guarda):
        self.guarda = guarda

    def get_formato_trama(self):
        return self.formato_trama

    def set_formato_trama(self, formato_trama):
        self.formato_trama = formato_trama
        self.txA_encabezado.set_header_format(self.formato_trama)
        self.txB_encabezado.set_header_format(self.formato_trama)
        self.rxA_ref_encabezado.set_header_format(self.formato_trama)
        self.rxB_ref_encabezado.set_header_format(self.formato_trama)

    def get_excess_bw(self):
        return self.excess_bw

    def set_excess_bw(self, excess_bw):
        self.excess_bw = excess_bw
        self.rxA_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))
        self.rxB_filtro_adaptado.set_taps(firdes.root_raised_cosine(1, self.samp_rate, (self.samp_rate/self.sps), self.excess_bw, (11*self.sps)))

    def get_L_B(self):
        return self.L_B

    def set_L_B(self, L_B):
        self.L_B = L_B
        self.txB_a_paquetes.set_packet_len(self.L_B)
        self.txB_a_paquetes.set_packet_len_pmt(self.L_B)
        self.rxA_ref_a_paquetes.set_packet_len(self.L_B)
        self.rxA_ref_a_paquetes.set_packet_len_pmt(self.L_B)

    def get_L_A(self):
        return self.L_A

    def set_L_A(self, L_A):
        self.L_A = L_A
        self.txA_a_paquetes.set_packet_len(self.L_A)
        self.txA_a_paquetes.set_packet_len_pmt(self.L_A)
        self.rxB_ref_a_paquetes.set_packet_len(self.L_A)
        self.rxB_ref_a_paquetes.set_packet_len_pmt(self.L_A)



def argument_parser():
    description = 'El mismo enlace half-duplex de halfduplex_4qam.grc, sin gráficos, para medir BER por línea de comandos'
    parser = ArgumentParser(description=description)
    parser.add_argument(
        "--ebn0-db", dest="ebn0_db", type=eng_float, default=eng_notation.num_to_str(float(6.0)),
        help="Set Eb/N0 [dB] [default=%(default)r]")
    parser.add_argument(
        "--fase-deg", dest="fase_deg", type=eng_float, default=eng_notation.num_to_str(float(0.0)),
        help="Set Fase del canal [grados] [default=%(default)r]")
    parser.add_argument(
        "--cfo-hz", dest="cfo_hz", type=eng_float, default=eng_notation.num_to_str(float(0.0)),
        help="Set Desvio entre osciladores A-B [Hz] [default=%(default)r]")
    parser.add_argument(
        "--costas-bw", dest="costas_bw", type=eng_float, default=eng_notation.num_to_str(float(0.005)),
        help="Set BW del lazo de Costas (0 = sin corregir fase) [default=%(default)r]")
    parser.add_argument(
        "--sync-bw", dest="sync_bw", type=eng_float, default=eng_notation.num_to_str(float(0.01)),
        help="Set BW del sincronismo de simbolo [default=%(default)r]")
    parser.add_argument(
        "--muestras", dest="muestras", type=intx, default=4000000,
        help="Set Muestras del canal compartido [default=%(default)r]")
    parser.add_argument(
        "--semilla", dest="semilla", type=intx, default=1,
        help="Set Semilla del ruido [default=%(default)r]")
    parser.add_argument(
        "--descartar", dest="descartar", type=intx, default=100000,
        help="Set Bits descartados al inicio (enganche de los lazos) [default=%(default)r]")
    return parser


def main(top_block_cls=halfduplex_4qam_ber, options=None):
    if options is None:
        options = argument_parser().parse_args()
    tb = top_block_cls(ebn0_db=options.ebn0_db, fase_deg=options.fase_deg, cfo_hz=options.cfo_hz, costas_bw=options.costas_bw, sync_bw=options.sync_bw, muestras=options.muestras, semilla=options.semilla, descartar=options.descartar)

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    tb.wait()


if __name__ == '__main__':
    main()
