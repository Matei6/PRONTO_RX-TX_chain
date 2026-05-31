#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Spino Rx Lf Setup
# GNU Radio version: 3.10.12.0

from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
from gnuradio import zeromq
from gnuradio.fft import logpwrfft
from xmlrpc.server import SimpleXMLRPCServer
import threading
import spino_rx_lf_setup_epy_block_5 as epy_block_5  # embedded python block



class spino_rx_lf_setup(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Spino Rx Lf Setup", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.volume = volume = 0.1
        self.seuil = seuil = -75
        self.samp_rate = samp_rate = 240000
        self.samp_per_sym = samp_per_sym = 20
        self.rbw_num = rbw_num = 10000
        self.gain_dB = gain_dB = 25
        self.fsk_deviation_Hz = fsk_deviation_Hz = 3600
        self.freq_num = freq_num = 0
        self.freq_MHz = freq_MHz = 435.2e6
        self.baud = baud = 2400

        ##################################################
        # Blocks
        ##################################################

        self.zeromq_pub_sink_0 = zeromq.pub_sink(gr.sizeof_float, 1024, 'tcp://127.0.0.1:5557', 100, False, (-1), '', True, True)
        self.zeromq_pub_msg_sink_0 = zeromq.pub_msg_sink('tcp://*:5555', 100, True)
        self.xmlrpc_server_0 = SimpleXMLRPCServer(('127.0.0.1', 8080), allow_none=True)
        self.xmlrpc_server_0.register_instance(self)
        self.xmlrpc_server_0_thread = threading.Thread(target=self.xmlrpc_server_0.serve_forever)
        self.xmlrpc_server_0_thread.daemon = True
        self.xmlrpc_server_0_thread.start()
        self.uhd_usrp_source_1 = uhd.usrp_source(
            ",".join(("", '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_1.set_samp_rate(samp_rate)
        self.uhd_usrp_source_1.set_time_unknown_pps(uhd.time_spec(0))

        self.uhd_usrp_source_1.set_center_freq(freq_MHz, 0)
        self.uhd_usrp_source_1.set_antenna("TX/RX", 0)
        self.uhd_usrp_source_1.set_gain(10, 0)
        self.logpwrfft_x_0 = logpwrfft.logpwrfft_c(
            sample_rate=samp_rate,
            fft_size=1024,
            ref_scale=2,
            frame_rate=30,
            avg_alpha=1.0,
            average=False,
            shift=True)
        self.epy_block_5 = epy_block_5.burst_to_pdu(max_len=1936)
        self.digital_symbol_sync_xx_0 = digital.symbol_sync_ff(
            digital.TED_MUELLER_AND_MULLER,
            (48000/baud),
            0.005,
            0.707,
            1.0,
            0.00766,
            1,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.digital_correlate_access_code_tag_xx_0_0 = digital.correlate_access_code_tag_bb('00101110111111001001100000100111', 1, 'burst')
        self.digital_binary_slicer_fb_0_0 = digital.binary_slicer_fb()
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_multiply_xx_1 = blocks.multiply_vcc(1)
        self.blocks_multiply_xx_0 = blocks.multiply_vcc(1)
        self.blocks_delay_0 = blocks.delay(gr.sizeof_gr_complex*1, 1)
        self.blocks_conjugate_cc_0 = blocks.conjugate_cc()
        self.blocks_complex_to_arg_0 = blocks.complex_to_arg(1)
        self.band_pass_filter_2 = filter.fir_filter_ccc(
            5,
            firdes.complex_band_pass(
                1000,
                (samp_rate/5),
                (-1.8e3),
                1.8e3,
                50,
                window.WIN_BLACKMAN,
                6.76))
        self.band_pass_filter_0 = filter.fir_filter_ccc(
            1,
            firdes.complex_band_pass(
                1,
                samp_rate,
                (freq_num-rbw_num/2),
                (freq_num+rbw_num/2),
                5000,
                window.WIN_RECTANGULAR,
                6.76))
        self.analog_simple_squelch_cc_0 = analog.simple_squelch_cc(seuil, 1)
        self.analog_sig_source_x_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (-freq_num), 1, 0, 0)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.epy_block_5, 'out'), (self.zeromq_pub_msg_sink_0, 'in'))
        self.connect((self.analog_sig_source_x_0, 0), (self.blocks_multiply_xx_0, 1))
        self.connect((self.analog_simple_squelch_cc_0, 0), (self.blocks_multiply_xx_0, 0))
        self.connect((self.analog_simple_squelch_cc_0, 0), (self.logpwrfft_x_0, 0))
        self.connect((self.band_pass_filter_0, 0), (self.analog_simple_squelch_cc_0, 0))
        self.connect((self.band_pass_filter_2, 0), (self.blocks_delay_0, 0))
        self.connect((self.band_pass_filter_2, 0), (self.blocks_multiply_xx_1, 0))
        self.connect((self.blocks_complex_to_arg_0, 0), (self.digital_symbol_sync_xx_0, 0))
        self.connect((self.blocks_conjugate_cc_0, 0), (self.blocks_multiply_xx_1, 1))
        self.connect((self.blocks_delay_0, 0), (self.blocks_conjugate_cc_0, 0))
        self.connect((self.blocks_multiply_xx_0, 0), (self.band_pass_filter_2, 0))
        self.connect((self.blocks_multiply_xx_1, 0), (self.blocks_complex_to_arg_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.band_pass_filter_0, 0))
        self.connect((self.digital_binary_slicer_fb_0_0, 0), (self.digital_correlate_access_code_tag_xx_0_0, 0))
        self.connect((self.digital_correlate_access_code_tag_xx_0_0, 0), (self.epy_block_5, 0))
        self.connect((self.digital_symbol_sync_xx_0, 0), (self.digital_binary_slicer_fb_0_0, 0))
        self.connect((self.logpwrfft_x_0, 0), (self.zeromq_pub_sink_0, 0))
        self.connect((self.uhd_usrp_source_1, 0), (self.blocks_throttle2_0, 0))

    def get_volume(self):
        return self.volume

    def set_volume(self, volume):
        self.volume = volume

    def get_seuil(self):
        return self.seuil

    def set_seuil(self, seuil):
        self.seuil = seuil
        self.analog_simple_squelch_cc_0.set_threshold(self.seuil)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.analog_sig_source_x_0.set_sampling_freq(self.samp_rate)
        self.band_pass_filter_0.set_taps(firdes.complex_band_pass(1, self.samp_rate, (self.freq_num-self.rbw_num/2), (self.freq_num+self.rbw_num/2), 5000, window.WIN_RECTANGULAR, 6.76))
        self.band_pass_filter_2.set_taps(firdes.complex_band_pass(1000, (self.samp_rate/5), (-1.8e3), 1.8e3, 50, window.WIN_BLACKMAN, 6.76))
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.logpwrfft_x_0.set_sample_rate(self.samp_rate)
        self.uhd_usrp_source_1.set_samp_rate(self.samp_rate)

    def get_samp_per_sym(self):
        return self.samp_per_sym

    def set_samp_per_sym(self, samp_per_sym):
        self.samp_per_sym = samp_per_sym

    def get_rbw_num(self):
        return self.rbw_num

    def set_rbw_num(self, rbw_num):
        self.rbw_num = rbw_num
        self.band_pass_filter_0.set_taps(firdes.complex_band_pass(1, self.samp_rate, (self.freq_num-self.rbw_num/2), (self.freq_num+self.rbw_num/2), 5000, window.WIN_RECTANGULAR, 6.76))

    def get_gain_dB(self):
        return self.gain_dB

    def set_gain_dB(self, gain_dB):
        self.gain_dB = gain_dB

    def get_fsk_deviation_Hz(self):
        return self.fsk_deviation_Hz

    def set_fsk_deviation_Hz(self, fsk_deviation_Hz):
        self.fsk_deviation_Hz = fsk_deviation_Hz

    def get_freq_num(self):
        return self.freq_num

    def set_freq_num(self, freq_num):
        self.freq_num = freq_num
        self.analog_sig_source_x_0.set_frequency((-self.freq_num))
        self.band_pass_filter_0.set_taps(firdes.complex_band_pass(1, self.samp_rate, (self.freq_num-self.rbw_num/2), (self.freq_num+self.rbw_num/2), 5000, window.WIN_RECTANGULAR, 6.76))

    def get_freq_MHz(self):
        return self.freq_MHz

    def set_freq_MHz(self, freq_MHz):
        self.freq_MHz = freq_MHz
        self.uhd_usrp_source_1.set_center_freq(self.freq_MHz, 0)

    def get_baud(self):
        return self.baud

    def set_baud(self, baud):
        self.baud = baud
        self.digital_symbol_sync_xx_0.set_sps((48000/self.baud))




def main(top_block_cls=spino_rx_lf_setup, options=None):
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
