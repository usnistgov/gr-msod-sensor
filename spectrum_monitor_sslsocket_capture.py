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
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math
import threading
import msod_sensor as myblocks
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
import signal
from multiprocessing import Process

def getLocalUtcTimeStamp():
    t = time.mktime(time.gmtime())
    isDst = time.localtime().tm_isdst
    return t - isDst * 60 * 60


def formatTimeStampLong(timeStamp, timeZoneName):
    """
    long format timestamp.
    """
    localTimeStamp, tzName = getLocalTime(timeStamp, timeZoneName)
    dt = datetime.datetime.fromtimestamp(float(localTimeStamp))
    return str(dt) + " " + tzName

class Struct(dict):
    def __init__(self, **kwargs):
	super(Struct, self).__init__(**kwargs)
	self.__dict__ = self

class ThreadClass(threading.Thread):
    def run(self):
        return

class my_top_block(gr.top_block):


    def read_configuration(self):
    	print 'host:',self.dest_host
    	sensor_id= self.sensorId
    	r = requests.post('https://'+self.dest_host+':443/sensordata/getStreamingPort/'+sensor_id, verify=False)
    	print 'Requestion port on:'+ 'https://'+self.dest_host+':443/sensordata/getStreamingPort/'+sensor_id 
    	print 'server response:', r.text
    	json = r.json()
    	port = json["port"]
    	print 'socket port =',port #, response['port']
    	self.port = port
    	print 'Requestion port on:'+ 'https://'+self.dest_host+':443/sensordb/getSensorConfig/'+sensor_id
    	r = requests.post('https://'+self.dest_host+':443/sensordb/getSensorConfig/'+sensor_id, verify=False)
    	print 'server response:', r.text
    	json = r.json()

    def initialize_message_headers(self):
    	self.loc_msg = self.read_json_from_file('sensor.loc')
    	self.sys_msg = self.read_json_from_file('sensor.sys')
    	self.data_msg = self.read_json_from_file('sensor.data')
    	ts = long(round(getLocalUtcTimeStamp()))
    	self.loc_msg['t'] = ts
    	self.loc_msg['SensorID'] = self.sensorId
    	self.sys_msg['t'] = ts
    	self.sys_msg['SensorID'] = self.sensorId
    	self.data_msg['t'] = ts
    	self.data_msg['t1'] = ts
    	# Fix up the data message in accordance with various input parameters.
    	f_start = int(self.center_freq - self.bandwidth / 2.0 -0.5)
    	f_stop = int (f_start + self.bandwidth + 0.5)
    	det = 'Average' if self.det_type == 'avg' else 'Peak'
    	self.data_msg['SensorID'] = self.sensorId
    	self.data_msg['mPar']['fStart'] = f_start
    	self.data_msg['mPar']['fStop'] = f_stop
    	self.data_msg['mPar']['Atten'] = self.atten
    	self.data_msg['mPar']['n'] = self.num_ch
    	self.data_msg['mPar']['tm'] = self.meas_duration

    def __init__(self):
        gr.top_block.__init__(self)

        usage = "usage: %prog [options] center_freq band_width"
        parser = OptionParser(option_class=eng_option, usage=usage)
        parser.add_option("-a", "--args", type="string", default="",
                          help="UHD device device address args [default=%default]")
        parser.add_option("", "--spec", type="string", default=None,
	                  help="Subdevice of UHD device where appropriate")
        parser.add_option("-A", "--antenna", type="string", default=None,
                          help="select Rx Antenna where appropriate")
        parser.add_option("-s", "--samp-rate", type="eng_float", default=1e6,
                          help="set sample rate [default=%default]")
        parser.add_option("-g", "--gain", type="eng_float", default=None,
                          help="set gain in dB (default is midpoint)")
        parser.add_option("", "--meas-interval", type="eng_float",
                          default=0.1, metavar="SECS",
                          help="interval over which to measure statistic (in seconds) [default=%default]")
    	parser.add_option("-t", "--det-type", type="string", default="avg",
                          help="set detection type ('avg' or 'peak') [default=%default]")
        parser.add_option("-c", "--number-channels", type="int", default=100, 
                          help="number of uniform channels for which to report power measurements [default=%default]")
        parser.add_option("-l", "--lo-offset", type="eng_float",
                          default=0, metavar="Hz",
                          help="lo_offset in Hz [default=half the sample rate]")
        parser.add_option("-F", "--fft-size", type="int", default=1024,
                          help="specify number of FFT bins [default=%default]")
        parser.add_option("", "--real-time", action="store_true", default=False,
                          help="Attempt to enable real-time scheduling")
    	parser.add_option("-d", "--dest-host", type="string", default="",
                          help="set destination host for streaming data")
        parser.add_option("", "--skip-DC", action="store_true", default=False,
                          help="skip the DC bin when mapping channels")
	parser.add_option("-S","--sensorId", type = "string", default = None, help="Sensor ID -- default will use serial number of sensor")
	parser.add_option("-m","--mongod_port", type = "int", default = 2017, help="Mongodb port")

        (options, args) = parser.parse_args()
        if len(args) != 2:
            parser.print_help()
            sys.exit(1)

	self.center_freq = eng_notation.str_to_num(args[0])
	self.bandwidth = eng_notation.str_to_num(args[1])
	self.dest_host = options.dest_host
	self.samp_rate = options.samp_rate
        self.fft_size = options.fft_size
        self.num_ch = options.number_channels
	self.sensorId = options.sensorId
	self.det_type = options.det_type
	self.mongodb_port = options.mongod_port

	self.read_configuration()


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
        self.u = uhd.usrp_source(device_addr=options.args,
                                 stream_args=uhd.stream_args('fc32'))

        # Set the subdevice spec
        if(options.spec):
            self.u.set_subdev_spec(options.spec, 0)

        # Set the antenna
        if(options.antenna):
            self.u.set_antenna(options.antenna, 0)
        
        self.u.set_samp_rate(options.samp_rate)
        usrp_rate = self.u.get_samp_rate()

	if usrp_rate != options.samp_rate:
	    if usrp_rate < options.samp_rate:
	        # create list of allowable rates
	        samp_rates = self.u.get_samp_rates()
	        rate_list = [0.0]*len(samp_rates)
	        for i in range(len(rate_list)):
		    last_rate = samp_rates.pop()
		    rate_list[len(rate_list) - 1 - i] = last_rate.start()
		# choose next higher rate
		rate_ind = rate_list.index(usrp_rate) + 1
		if rate_ind < len(rate_list):
		    self.u.set_samp_rate(rate_list[rate_ind])
		    usrp_rate = self.u.get_samp_rate()
		print "New actual sample rate =", usrp_rate/1e6, "MHz"
	    resamp = filter.fractional_resampler_cc(0.0, usrp_rate / options.samp_rate)

        
	if(options.lo_offset):
            self.lo_offset = options.lo_offset
	else:
	    self.lo_offset = usrp_rate / 2.0
	    print "LO offset set to", self.lo_offset/1e6, "MHz"

        
        s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)

        mywindow = filter.window.blackmanharris(self.fft_size)
        ffter = fft.fft_vcc(self.fft_size, True, mywindow, True)
        window_power = sum(map(lambda x: x*x, mywindow))

        c2mag = blocks.complex_to_mag_squared(self.fft_size)

	self.bin2ch_map = [0] * self.fft_size
        hz_per_bin = self.samp_rate / self.fft_size
	channel_bw = hz_per_bin * round(self.bandwidth / self.num_ch / hz_per_bin)
	self.bandwidth = channel_bw * self.num_ch
	self.start_freq = int(self.center_freq - self.bandwidth/2.0 -0.5)
	self.stop_freq = int (self.start_freq + self.bandwidth +0.5)



	for j in range(self.fft_size):
	    fj = self.bin_freq(j, self.center_freq)
	    if (fj >= self.start_freq) and (fj < self.stop_freq):
	        channel_num = int(math.floor((fj - self.start_freq) / channel_bw)) + 1
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

	self.det_type = options.det_type
	det = 0 if self.det_type=='avg' else 1
        self.stats = myblocks.bin_statistics_ff(self.num_ch, meas_frames, det)

	# Divide magnitude-square by a constant to obtain power
	# in Watts.  Assumes unit of USRP source is volts.
	impedance = 50.0   # ohms
	Vsq2W_dB = -10.0 * math.log10(self.fft_size * window_power * impedance)

	# Convert from Watts to dBm.
	W2dBm = blocks.nlog10_ff(10.0, self.num_ch, 30.0 + Vsq2W_dB)

	f2c = blocks.float_to_char(self.num_ch, 1.0)
        g = self.u.get_gain_range()
        if options.gain is None:
            # if no gain was specified, use the mid-point in dB
            options.gain = float(g.start()+g.stop())/2.0

        self.set_gain(options.gain)
        print "gain =", options.gain, "dB in range (%0.1f dB, %0.1f dB)" % (float(g.start()), float(g.stop()))
	self.atten = float(g.stop()) - options.gain

        capture_sink = myblocks.capture_sink(itemsize=gr.sizeof_gr_complex, chunksize = 500, capture_dir="/tmp", mongodb_port=self.mongodb_port)
	self.initialize_message_headers()
	trigger = myblocks.dummy_capture_trigger(itemsize=gr.sizeof_gr_complex)
	# Note: pass the trigger here so the trigger can be armed.
	self.sslsocket_sink = myblocks.sslsocket_sink(numpy.int8, self.num_ch,self.dest_host,self.port,self.sys_msg,self.loc_msg,self.data_msg,capture_sink,trigger,os.getppid())

	if usrp_rate > self.samp_rate:
	    self.connect(self.u, resamp, s2v)
	else:
	    self.connect(self.u, s2v)

	# Connect the blocks together.
	self.connect(s2v, ffter, c2mag, self.aggr, self.stats, W2dBm, f2c, self.sslsocket_sink)
	# Second pipeline to the sink.
	self.connect(self.u,trigger,capture_sink)
	self.msg_connect(trigger,"trigger",capture_sink,"capture")

    def disconnect(self):
	self.sslsocket_sink.disconnect()

    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        Args:
            target_freq: frequency in Hz
        @rypte: bool
        """
        
        r = self.u.set_center_freq(uhd.tune_request(target_freq, rf_freq=(target_freq + self.lo_offset),rf_freq_policy=uhd.tune_request.POLICY_MANUAL))
        if r:
            return True

        return False

    def set_gain(self, gain):
        self.u.set_gain(gain)
    
    def bin_freq(self, i_bin, center_freq):
        hz_per_bin = self.samp_rate / self.fft_size
	# For odd fft_size, treats i_bin = (fft_size + 1) / 2 as the DC bin.
        freq = center_freq + hz_per_bin * (i_bin - self.fft_size / 2 - self.fft_size % 2)
        return freq
    
    def send(self, bytes):
	#toSend = binascii.b2a_base64(bytes)
	#self.s.send(toSend)
	self.s.send(bytes)


    def set_bin2ch_map(self, bin2ch_map):
        self.aggr.set_bin_index(bin2ch_map)

    def read_json_from_file(self, fname):
	f = open(fname,'r')
	obj = json.load(f)
	f.close()
        return obj

def main_loop(tb):
    print 'starting main loop' 
    if not tb.set_freq(tb.center_freq):
        print "Failed to set frequency to", tb.center_freq
        sys.exit(1)
    print "Set frequency to", tb.center_freq/1e6, "MHz"
    time.sleep(0.25)
  

    # Start flow graph
    tb.start()
    tb.wait()
    tb.s.close()
    print 'Closed socket'

def start_main_loop():
    signal.signal(signal.SIGUSR1,sigusr1_handler)
    tb = my_top_block()
    try:
        main_loop(tb)
    except KeyboardInterrupt:
	pass

def sigusr1_handler(signo,frame):
	print "got a signal " + str(signo)
	# TODO -- reconfigure the system here.
	# TODO -- close 
	tb.stop()
	tb.disconnect()
	os.kill(signal.SIGUSR2,os.getppid())
	sys.exit()
	os._exit_()

def sigusr2_handler(signo,frame):
    print "Got sigusr2 restarting loop."
    time.sleep(10)
    p = Process(target=start_main_loop)
    p.start()
	
if __name__ == '__main__':
    t = ThreadClass()
    t.start()
    signal.signal(signal.SIGUSR1,sigusr2_handler)
    p = Process(target=start_main_loop)
    p.start()

  
