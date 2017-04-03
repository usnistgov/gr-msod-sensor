#!/usr/bin/env python
#
# Copyright 2005,2007,2011 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import gr, eng_notation
from gnuradio import blocks
from gnuradio import filter
from gnuradio import fft
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math
import threading
import myblocks
import array
import time
import json
import socket
import ssl
import requests
#import binascii
import numpy
import struct
import os
#sys.path.insert(0,os.environ['SPECTRUM_BROWSER_HOME']+'/flask')
from timezone import getLocalUtcTimeStamp, formatTimeStampLong
import osmosdr, subprocess

class Struct(dict):
    def __init__(self, **kwargs):
	super(Struct, self).__init__(**kwargs)
	self.__dict__ = self

class ThreadClass(threading.Thread):
    def run(self):
        return

class my_top_block(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self)

        usage = "usage: %prog [options] center_freq band_width"
        parser = OptionParser(option_class=eng_option, usage=usage)
        parser.add_option("-s", "--samp-rate", type="eng_float", default=10e6,
                          help="set sample rate: 8/10/12.5/16/20 MHz [default=%default]")
        parser.add_option("-g", "--rf-gain", type="eng_float", default=0,
                          help="set the overall gain in dB (default is midpoint)") #FIXME range?
        parser.add_option("", "--lna-gain", type="eng_float", default=24,
                          help="set RX IF gain in dB (default is midpoint): 0-40dB, 8dB steps")
        parser.add_option("", "--vga-gain", type="eng_float", default=32,
                          help="set BB gain in dB (default is midpoint): 0-62dB, 2dB steps")
        parser.add_option("", "--antenna", action="store_false", default=True,
                          help="Disable Antenna Port Power [default=%default]")
        parser.add_option("", "--bandwidth", type="eng_float", default=10e6,
                          help="Set the BB Filter Bandwidth in MHz: 1.75-28 MHz[default=%default]")
        parser.add_option("", "--g-mode", action="store_false", default=True,
                          help="set the gain mode[default=%default]")
        parser.add_option("", "--iq-balance", type="eng_float", default=2,
                          help="set the iq_balance_mode [default=%default]")
	parser.add_option("", "--dc-off", type="eng_float", default=1,
                          help="set the dc offset mode [default=%default]")

        parser.add_option("", "--meas-interval", type="eng_float",
                          default=0.1, metavar="SECS",
                          help="interval over which to measure statistic (in seconds) [default=%default]")
        parser.add_option("-c", "--number-channels", type="int", default=56,
                          help="number of uniform channels for which to report power measurements [default=%default]") 
        parser.add_option("-F", "--fft-size", type="int", default=1024,
                          help="specify number of FFT bins [default=%default]")
        parser.add_option("", "--real-time", action="store_true", default=False,
                          help="Attempt to enable real-time scheduling")
        parser.add_option("-d", "--dest-host", type="string", default="",
                          help="set destination host for sending data")
        parser.add_option("", "--skip-DC", action="store_true", default=False,
                          help="skip the DC bin when mapping channels")
        parser.add_option("", "--avoid-LO", action="store_true", default=False,
                          help="Avoid LO by sampling at higher rate, shift frequency and take only a desired chunk")

#        parser.add_option("-l", "--lo-offset", type="eng_float", default=0, metavar="Hz", 
#                          help="lo_offset in Hz [default=half the sample rate]")
#        parser.add_option("", "--tx-VGA-gain", type="eng_float", default=None,
#                          help="set TX IF gain in dB (default is midpoint): 0-47dB, 1dB steps")
        (options, args) = parser.parse_args()
        if len(args) != 2:
            parser.print_help()
            sys.exit(1)

	self.center_freq = eng_notation.str_to_num(args[0])
        if options.avoid_LO:
                self.center_freq = self.center_freq + options.samp_rate/4.0
		print "Avoiding LO...\nShifting center Frequency to", self.center_freq
	self.bandwidth = eng_notation.str_to_num(args[1])

        if not options.real_time:
            realtime = False
        else:
            # Attempt to enable realtime scheduling
            r = gr.enable_realtime_scheduling()
            if r == gr.RT_OK:
                realtime = True
            else:
                realtime = False
                print "Note: failed to enable realtime scheduling"

        # build graph
        self.u = osmosdr.source( args="numchan=" + str(1) + " " + "hackrf=0" )
        self.u.set_sample_rate(options.samp_rate)
        self.u.set_freq_corr(0, 0)
        self.u.set_dc_offset_mode(int(options.dc_off), 0)
        self.u.set_iq_balance_mode(int(options.iq_balance), 0)
	print "options.g_mode: ", options.g_mode
        self.u.set_gain_mode(options.g_mode, 0)
        self.u.set_gain(options.rf_gain, 0)
        self.u.set_if_gain(options.lna_gain, 0)
        self.u.set_bb_gain(options.vga_gain, 0)
        self.u.set_antenna("", 0)
        self.u.set_bandwidth(options.bandwidth, 0)

        #if hackrf_rate != options.samp_rate: #FIXME How to read back hackrf_rate
        #    if hackrf_rate < options.samp_rate:
        #        # create list of allowable rates
        #        samp_rates = self.u.get_samp_rates()
        #        rate_list = [0.0]*len(samp_rates)
        #        for i in range(len(rate_list)):
        #           last_rate = samp_rates.pop()
        #           rate_list[len(rate_list) - 1 - i] = last_rate.start()
        #       # choose next higher rate
        #       rate_ind = rate_list.index(hackrf_rate) + 1
        #       if rate_ind < len(rate_list):
        #           self.u.set_samp_rate(rate_list[rate_ind])
        #           hackrf_rate = self.u.get_samp_rate()
        #       print "New actual sample rate =", hackrf_rate/1e6, "MHz"
        #    resamp = filter.fractional_resampler_cc(0.0, hackrf_rate / options.samp_rate)
	
	self.samp_rate = options.samp_rate
        self.fft_size = options.fft_size
        self.num_ch = options.number_channels
        self.avoid_LO = options.avoid_LO 

        s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)

        mywindow = filter.window.blackmanharris(self.fft_size)
        ffter = fft.fft_vcc(self.fft_size, True, mywindow, True)
        window_power = sum(map(lambda x: x*x, mywindow))

        c2mag = blocks.complex_to_mag_squared(self.fft_size)
	self.bin2ch_map = [0] * self.fft_size
        hz_per_bin = self.samp_rate / self.fft_size
	print "\nhz_per_bin: ", hz_per_bin/1e3, "kHz"
	channel_bw = hz_per_bin * round(self.bandwidth / self.num_ch / hz_per_bin)
	print "RB Bandwidth: ", channel_bw/1e3, "kHz"
	self.bandwidth = channel_bw * self.num_ch
	print "Actual width of band is", self.bandwidth/1e6, "MHz."
        start_freq = self.center_freq - self.bandwidth/2.0
        #print "Initiallay set frequency range to: [",start_freq/1e6, "MHz-",stop_freq/1e6,"MHz ]"
        if options.avoid_LO:
                start_freq = (self.center_freq - options.samp_rate/4) - self.bandwidth/2.0
        stop_freq = start_freq + self.bandwidth
        if options.avoid_LO:
                print "Avoiding LO, frequencies are shifted to: [",start_freq/1e6, "MHz-",stop_freq/1e6,"MHz ]"

	for j in range(self.fft_size):
	    fj = self.bin_freq(j, self.center_freq)
	    if (fj >= start_freq) and (fj < stop_freq):
	        channel_num = int(math.floor((fj - start_freq) / channel_bw)) + 1
	        self.bin2ch_map[j] = channel_num
	if options.skip_DC:
	    self.bin2ch_map[(self.fft_size + 1) / 2 + 1:] = self.bin2ch_map[(self.fft_size + 1) / 2 : -1]
	    self.bin2ch_map[(self.fft_size + 1) / 2] = 0
	if self.bandwidth > self.samp_rate:
	    print "Warning: Width of band (" + str(self.bandwidth/1e6), "MHz) is greater than the sample rate (" + str(self.samp_rate/1e6), "MHz)."

	self.aggr = myblocks.bin_aggregator_ff(self.fft_size, self.num_ch, self.bin2ch_map)

        meas_frames = max(1, int(round(options.meas_interval * self.samp_rate / self.fft_size))) # in fft_frames
	self.meas_duration = meas_frames * self.fft_size / self.samp_rate
	print "Actual measurement duration =", self.meas_duration, "s"

        self.stats = myblocks.bin_statistics_ff(self.num_ch, meas_frames)

	# Divide magnitude-square by a constant to obtain power
	# in Watts.  Assumes unit of HackRF source is volts.
	impedance = 50.0   # ohms
	Vsq2W_dB = -10.0 * math.log10(self.fft_size * window_power * impedance)

	# Convert from Watts to dBm.
	W2dBm = blocks.nlog10_ff(10.0, self.num_ch, 30.0 + Vsq2W_dB)

	f2c = blocks.float_to_char(self.num_ch, 1.0)

	self.dest_host = options.dest_host

	# ssl socket is set in main loop; use dummy value for now
	self.srvr = myblocks.sslsocket_sink(numpy.int8, self.num_ch, 0)

	if options.samp_rate > self.samp_rate:
	    # insert resampler
	    self.connect(self.u, resamp, s2v)
	else:
	    self.connect(self.u, s2v)
	self.connect(s2v, ffter, c2mag, self.aggr, self.stats, W2dBm, f2c, self.srvr)
	#self.connect(s2v, ffter, c2mag, self.aggr, self.stats, W2dBm, self.srvr)

        g_start = 0
        g_stop  = 20
        # FIXME Find out the Gain range of HACK_RF
        if options.rf_gain is None:
            # if no gain was specified, use the mid-point in dB
            options.rf_gain = float(g_start+g_stop)/2.0
        self.set_gain(options.rf_gain)

        print "gain =", options.rf_gain, "dB in range (%0.1f dB, %0.1f dB)" % (float(g_start), float(g_stop))
	self.atten = float(g_stop) - options.rf_gain
 
    def set_freq(self, target_freq):
        """ 
        Set the center frequency we're interested in.

        Args:
            target_freq: frequency in Hz
        @rypte: bool
        """
        r = self.u.set_center_freq(target_freq) 
        return True

    def set_gain(self, gain):
        self.u.set_gain(gain)
    
    def bin_freq(self, i_bin, center_freq):
        hz_per_bin = self.samp_rate / self.fft_size
	# For odd fft_size, treats i_bin = (fft_size + 1) / 2 as the DC bin.
        freq = center_freq + hz_per_bin * (i_bin - self.fft_size / 2 - self.fft_size % 2)
        return freq
    
    def set_sock(self, s):
        self.srvr.set_sock(s)

    def send(self, bytes):
	#toSend = binascii.b2a_base64(bytes)
	#self.s.send(toSend)
	self.s.send(bytes)

    def send_obj(self, obj):
	msg = json.dumps(obj)
	frmt = "=%ds" % len(msg)
	packed_msg = struct.pack(frmt, msg)
	ascii_hdr = "%d\r" % len(packed_msg)
	self.send(ascii_hdr)
	self.send(packed_msg)

    def set_bin2ch_map(self, bin2ch_map):
        self.aggr.set_bin_index(bin2ch_map)

    def read_json_from_file(self, fname):
	f = open(fname,'r')
	obj = json.load(f)
	f.close()
        return obj

def main_loop(tb):
    
    if not tb.set_freq(tb.center_freq):
        print "Failed to set frequency to", tb.center_freq
        sys.exit(1)
    print "Set frequency to", tb.center_freq/1e6, "MHz\n"
    time.sleep(0.25)

    sensor_id = "HackRF"	   
    # Establish ssl socket connection to server
    r = requests.post('https://'+tb.dest_host+':8443/sensordata/getStreamingPort/'+sensor_id, verify=False)
    print 'server response:', r.text
    response = r.json()
    print 'socket port =', response['port']
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tb.s = s = ssl.wrap_socket(sock)#, ca_certs='dummy.crt', cert_reqs=ssl.CERT_NONE)
    s.connect((tb.dest_host, response['port']))
    tb.set_sock(s)

    # Send location and system info to server
    loc_msg = tb.read_json_from_file('sensor.loc')
    sys_msg = tb.read_json_from_file('sensor.sys')
    ts = long(round(getLocalUtcTimeStamp()))
    sensor_key = sys_msg['SensorKey']	
    print 'Sensor Key', sensor_key
    #print 'Serial no.', sensor_id

    loc_msg['t'] = ts
    loc_msg['SensorID'] = sensor_id 
    sys_msg['t'] = ts
    sys_msg['SensorID'] = sensor_id 
    tb.send_obj(loc_msg)
    tb.send_obj(sys_msg)

    # Form data header
    ts = long(round(getLocalUtcTimeStamp()))
    f_start = tb.center_freq - tb.bandwidth/2.0
    if tb.avoid_LO:
            f_start = (tb.center_freq - tb.samp_rate/4) - tb.bandwidth/2.0
    f_stop = f_start + tb.bandwidth
    if tb.avoid_LO:
            print "Avoiding LO, frequencies are shifted to: [",f_start/1e6, "MHz-",f_stop/1e6,"MHz ]"

    mpar = Struct(fStart=f_start, fStop=f_stop, n=tb.num_ch, td=-1, tm=tb.meas_duration, Det='Average', Atten=tb.atten)
    # Need to add a field for overflow indicator
    data = Struct(Ver='1.0.12', Type='Data', SensorID='HackRF', SensorKey='12345', t=ts, Sys2Detect='LTE', Sensitivity='Low', mType='FFT-Power', t1=ts, a=1, nM=-1, Ta=-1, OL='NaN', wnI=-77.0, Comment='Using hard-coded (not detected) system noise power for wnI', Processed='False', DataType = 'Binary - int8', ByteOrder='N/A', Compression='None', mPar=mpar)

    tb.send_obj(data)
    date_str = formatTimeStampLong(ts, loc_msg['TimeZone'])
    print date_str, "fc =", tb.center_freq/1e6, "MHz. Sending data to", tb.dest_host

    # Start flow graph
    tb.start()
    tb.wait()
    tb.s.close()
    print 'Closed socket'

if __name__ == '__main__':
    t = ThreadClass()
    t.start()

    tb = my_top_block()
    try:
        main_loop(tb)

    except KeyboardInterrupt:
	pass
