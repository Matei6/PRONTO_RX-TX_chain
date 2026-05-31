#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.10.12.0

from gnuradio import blocks
from gnuradio import blocks, gr
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import gr, pdu
from gnuradio import uhd
import time
from gnuradio import zeromq
import threading



class full_TX_chain(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.baud_rate = baud_rate = 2400
        self.fsk_deviation = fsk_deviation = baud_rate-400
        self.center = center = 0
        self.vco_max = vco_max = center+fsk_deviation
        self.samp_rate = samp_rate = 48000
        self.vco_offset = vco_offset = (center-(fsk_deviation/2))/vco_max
        self.rf_samp_rate = rf_samp_rate = 12e5
        self.repeat = repeat = (int)(samp_rate/baud_rate)
        self.sps = sps = samp_rate/baud_rate
        self.samp_per_sym = samp_per_sym = 20
        self.rf_decim = rf_decim = (int)(rf_samp_rate/(baud_rate*repeat))
        self.inp_amp = inp_amp = ((center+(fsk_deviation/2))/vco_max)-vco_offset
        self.data_size = data_size = 27*8

        ##################################################
        # Blocks
        ##################################################

        self.zeromq_pull_source_0 = zeromq.pull_source(gr.sizeof_char, 1, 'tcp://127.0.0.1:8669', 10000, False, (-1), True)
        self.uhd_usrp_sink_0 = uhd.usrp_sink(
            ",".join(('', '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
            "",
        )
        self.uhd_usrp_sink_0.set_samp_rate(rf_samp_rate)
        self.uhd_usrp_sink_0.set_time_unknown_pps(uhd.time_spec(0))

        self.uhd_usrp_sink_0.set_center_freq(145830e3, 0)
        self.uhd_usrp_sink_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_0.set_gain(68, 0)
        self.pdu_tagged_stream_to_pdu_0 = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'packet_len')
        self.blocks_vco_c_0 = blocks.vco_c(samp_rate, (2*3.141592*vco_max), 1)
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(8)
        self.blocks_uchar_to_float_0 = blocks.uchar_to_float()
        self.blocks_stream_to_tagged_stream_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, 47, "packet_len")
        self.blocks_repeat_1_0 = blocks.repeat(gr.sizeof_gr_complex*1, rf_decim)
        self.blocks_repeat_0 = blocks.repeat(gr.sizeof_float*1, repeat)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_ff(inp_amp)
        self.blocks_message_debug_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_add_const_vxx_0 = blocks.add_const_ff(vco_offset)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.pdu_tagged_stream_to_pdu_0, 'pdus'), (self.blocks_message_debug_0, 'print_pdu'))
        self.connect((self.blocks_add_const_vxx_0, 0), (self.blocks_vco_c_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_add_const_vxx_0, 0))
        self.connect((self.blocks_repeat_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_repeat_1_0, 0), (self.uhd_usrp_sink_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0, 0), (self.pdu_tagged_stream_to_pdu_0, 0))
        self.connect((self.blocks_uchar_to_float_0, 0), (self.blocks_repeat_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.blocks_uchar_to_float_0, 0))
        self.connect((self.blocks_vco_c_0, 0), (self.blocks_repeat_1_0, 0))
        self.connect((self.zeromq_pull_source_0, 0), (self.blocks_stream_to_tagged_stream_0, 0))
        self.connect((self.zeromq_pull_source_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))

    def get_baud_rate(self):
        return self.baud_rate

    def set_baud_rate(self, baud_rate):
        self.baud_rate = baud_rate
        self.set_fsk_deviation(self.baud_rate-400)
        self.set_repeat((int)(self.samp_rate/self.baud_rate))
        self.set_rf_decim((int)(self.rf_samp_rate/(self.baud_rate*self.repeat)))
        self.set_sps(self.samp_rate/self.baud_rate)

    def get_fsk_deviation(self):
        return self.fsk_deviation

    def set_fsk_deviation(self, fsk_deviation):
        self.fsk_deviation = fsk_deviation
        self.set_inp_amp(((self.center+(self.fsk_deviation/2))/self.vco_max)-self.vco_offset)
        self.set_vco_max(self.center+self.fsk_deviation)
        self.set_vco_offset((self.center-(self.fsk_deviation/2))/self.vco_max)

    def get_center(self):
        return self.center

    def set_center(self, center):
        self.center = center
        self.set_inp_amp(((self.center+(self.fsk_deviation/2))/self.vco_max)-self.vco_offset)
        self.set_vco_max(self.center+self.fsk_deviation)
        self.set_vco_offset((self.center-(self.fsk_deviation/2))/self.vco_max)

    def get_vco_max(self):
        return self.vco_max

    def set_vco_max(self, vco_max):
        self.vco_max = vco_max
        self.set_inp_amp(((self.center+(self.fsk_deviation/2))/self.vco_max)-self.vco_offset)
        self.set_vco_offset((self.center-(self.fsk_deviation/2))/self.vco_max)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_repeat((int)(self.samp_rate/self.baud_rate))
        self.set_sps(self.samp_rate/self.baud_rate)

    def get_vco_offset(self):
        return self.vco_offset

    def set_vco_offset(self, vco_offset):
        self.vco_offset = vco_offset
        self.set_inp_amp(((self.center+(self.fsk_deviation/2))/self.vco_max)-self.vco_offset)
        self.blocks_add_const_vxx_0.set_k(self.vco_offset)

    def get_rf_samp_rate(self):
        return self.rf_samp_rate

    def set_rf_samp_rate(self, rf_samp_rate):
        self.rf_samp_rate = rf_samp_rate
        self.set_rf_decim((int)(self.rf_samp_rate/(self.baud_rate*self.repeat)))
        self.uhd_usrp_sink_0.set_samp_rate(self.rf_samp_rate)

    def get_repeat(self):
        return self.repeat

    def set_repeat(self, repeat):
        self.repeat = repeat
        self.set_rf_decim((int)(self.rf_samp_rate/(self.baud_rate*self.repeat)))
        self.blocks_repeat_0.set_interpolation(self.repeat)

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps

    def get_samp_per_sym(self):
        return self.samp_per_sym

    def set_samp_per_sym(self, samp_per_sym):
        self.samp_per_sym = samp_per_sym

    def get_rf_decim(self):
        return self.rf_decim

    def set_rf_decim(self, rf_decim):
        self.rf_decim = rf_decim
        self.blocks_repeat_1_0.set_interpolation(self.rf_decim)

    def get_inp_amp(self):
        return self.inp_amp

    def set_inp_amp(self, inp_amp):
        self.inp_amp = inp_amp
        self.blocks_multiply_const_vxx_0.set_k(self.inp_amp)

    def get_data_size(self):
        return self.data_size

    def set_data_size(self, data_size):
        self.data_size = data_size




def main(top_block_cls=full_TX_chain, options=None):
    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    signal.pause()

if __name__ == '__main__':
    main()
