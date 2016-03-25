
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
import osmosdr
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math
import threading
import msod_sensor as myblocks
import array
import time
import json
import ssl
import requests
import numpy
import struct
import os
import signal
import traceback
from multiprocessing import Process

import argparse
import requests
from gnuradio.wxgui import stdgui2, form, slider
from gnuradio.wxgui import forms
from gnuradio.wxgui import fftsink2, waterfallsink2, scopesink2
import wx


import urllib3

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

#import urllib3.contrib.pyopenssl

#urllib3.contrib.pyopenssl.inject_into_urllib3()

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

def parse_options():
        usage = "usage: %prog [options]" #center_freq band_width"
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
    	parser.add_option("-t", "--det-type", type="string", default="avg",
                          help="set detection type ('avg' or 'peak') [default=%default]")
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
	parser.add_option("-m","--mongod-port", type = "int", default = 2017, help="Mongodb port")
        parser.add_option("", "--avg-alpha", type="eng_float", default=1e-1,
                          help="Set fftsink averaging factor, default=[%default]")
	parser.add_option("-u","--use-usrp", dest="use_usrp", action="store_false",  help = "Use usrp")
        parser.add_option("", "--fft-rate", type="int", default=30,
                          help="Set FFT update rate, [default=%default]")
        parser.add_option("", "--waterfall", action="store_true", default=False,
                          help="Enable waterfall display")
        parser.add_option("", "--fosphor", action="store_true", default=False,
                          help="Enable fosphor display")
        parser.add_option("", "--oscilloscope", action="store_true", default=False,
                          help="Enable oscilloscope display")
        parser.add_option("", "--ref-scale", type="eng_float", default=1.0,
                          help="Set dBFS=0dB input value, default=[%default]")
        parser.add_option("", "--impedance", type="eng_float", default=50.0,
                          help="Set dBFS=0dB input value, default=[%default]")

        (options, args) = parser.parse_args()
	return options,args


def init_osmosdr(options):
	u =  osmosdr.source(args=options.args)
       	u.set_sample_rate(options.samp_rate)
       	u.set_freq_corr(0, 0)
       	u.set_dc_offset_mode(1, 0)
	u.set_dc_offset(1,1)
       	u.set_iq_balance_mode(2, 0)
       	u.set_gain_mode(True, 0)
       	u.set_gain(6, 0)
       	u.set_if_gain(15, 0)
       	u.set_bb_gain(7, 0)
        try:
           u.get_sample_rates().start()
        except RuntimeError:
	   traceback.print_exc()
           print "Source has no sample rates (wrong device arguments?)."
           sys.exit(1)
	return u

class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_SSLv3)

class my_top_block(stdgui2.std_top_block):
    def read_configuration(self):
    	print 'host:',self.dest_host
    	sensor_id= self.sensorId
    	print 'Requestion port on:'+ 'https://'+self.dest_host+':443/sensordata/getStreamingPort/'+sensor_id 
    	r = requests.post('https://'+self.dest_host+':443/sensordata/getStreamingPort/'+sensor_id, verify=False)
    	print 'server response:', r.text
    	json = r.json()
    	port = json["port"]
    	print 'socket port =',port 
    	self.port = port
    	print 'Requestion port on:'+ 'https://'+self.dest_host+':443/sensordb/getSensorConfig/'+sensor_id
    	r = requests.post('https://'+self.dest_host+':443/sensordb/getSensorConfig/'+sensor_id, verify=False)
    	print 'server response:', r.text
    	json = r.json()


	#Reads in min & max frequency
	activeBands = json["sensorConfig"]["thresholds"]
	self.meas_interval = json["sensorConfig"]["streaming"]["streamingSecondsPerFrame"]
	for band in activeBands.values():
		if band["active"]:
			self.start_freq = band["minFreqHz"]
			self.stop_freq = band["maxFreqHz"]
			print str(band["minFreqHz"])
			print str(band["maxFreqHz"])
                        self.num_ch = band["channelCount"]



    def initialize_message_headers(self):
    	self.loc_msg = self.read_json_from_file('sensor.loc')
    	self.sys_msg = self.read_json_from_file('sensor.sys')
    	self.data_msg = self.read_json_from_file('sensor.data')
        self.event_msg = self.read_json_from_file('sensor.event')
    	ts = long(round(getLocalUtcTimeStamp()))
    	self.loc_msg['t'] = ts
    	self.loc_msg['SensorID'] = self.sensorId
    	self.sys_msg['t'] = ts
    	self.sys_msg['SensorID'] = self.sensorId
    	self.data_msg['t'] = ts
    	self.data_msg['t1'] = ts
    	# Fix up the data message in accordance with various input parameters.
    	det = 'Average' if self.det_type == 'avg' else 'Peak'
    	self.data_msg['SensorID'] = self.sensorId
    	self.data_msg['mPar']['fStart'] = self.start_freq
    	self.data_msg['mPar']['fStop'] = self.stop_freq
    	self.data_msg['mPar']['Atten'] = self.atten
    	#self.data_msg['mPar']['tm'] = self.meas_duration
    	self.data_msg['mPar']['tm'] = self.meas_interval
	
    	self.event_msg['SensorID'] = self.sensorId
    	self.event_msg['mPar']['fStart'] = self.start_freq
    	self.event_msg['mPar']['fStop'] = self.stop_freq
    	self.event_msg['mPar']['Atten'] = self.atten
    	self.event_msg['mPar']['n'] = self.num_ch
    	self.event_msg['mPar']['samp_rate'] = self.samp_rate

    def init_flow_graph(self):
	self.read_configuration()

        if not self.options.real_time:
            realtime = False
        else:
            # Attempt to enable realtime scheduling
            r = gr.enable_realtime_scheduling()
            if r == gr.RT_OK:
                realtime = True
            else:
                realtime = False
                print "Note: failed to enable realtime scheduling"

	if options.fosphor:
            from gnuradio import fosphor
            self.scope = fosphor.wx_sink_c(self.panel, size=(800,300))
            self.scope.set_sample_rate(input_rate)
            self.frame.SetMinSize((800,600))
        elif options.waterfall:
            self.scope = waterfallsink2.waterfall_sink_c (self.panel,
                                                          fft_size=options.fft_size,
                                                          sample_rate=options.samp_rate,
                                                          ref_scale=options.ref_scale,
                                                          ref_level=20.0,
                                                          y_divs = 12)
            self.frame.SetMinSize((800, 420))
        elif options.oscilloscope:
            self.scope = scopesink2.scope_sink_c(self.panel, sample_rate=input_rate)
            self.frame.SetMinSize((800, 600))
        else:
            self.scope = fftsink2.fft_sink_c (self.panel,
                                              fft_size=options.fft_size,
                                              sample_rate=options.samp_rate,
                                              ref_scale=options.ref_scale,
                                              ref_level=20.0,
                                              y_divs = 12,
                                              average= self.det_type == 'avg' ,
                                              peak_hold= self.det_type == 'peak',
                                              avg_alpha=options.avg_alpha,
                                              fft_rate=options.fft_rate)
            self.frame.SetMinSize((800,600))
        if hasattr(self.scope, 'set_sample_rate'):
            self.scope.set_sample_rate(options.samp_rate)



	# build graph.. TODO -- cut over to OSMO SDR and get rid of USRP
	self.use_usrp = self.options.use_usrp

        
        usrp_rate = self.u.get_sample_rate()
        if usrp_rate != self.options.samp_rate:
	      if usrp_rate < self.options.samp_rate:
	         # create list of allowable rates
	         samp_rates = self.u.get_sample_rates()
	         rate_list = [0.0]*len(samp_rates)
	         for i in range(len(rate_list)):
		    last_rate = samp_rates.pop()
		    rate_list[len(rate_list) - 1 - i] = last_rate.start()
		 # choose next higher rate
		 rate_ind = rate_list.index(usrp_rate) + 1
		 if rate_ind < len(rate_list):
		    self.u.set_samp_rate(rate_list[rate_ind])
		    usrp_rate = self.u.get_sample_rate()
		 print "New actual sample rate =", usrp_rate/1e6, "MHz"
	      resamp = filter.fractional_resampler_cc(0.0, usrp_rate / self.options.samp_rate)

	print "sample rate " , usrp_rate

        # Set the antenna
        if(self.options.antenna):
            self.u.set_antenna(self.options.antenna)
         
	if(self.options.use_usrp and self.options.lo_offset):
            self.lo_offset = self.options.lo_offset
	elif self.options.use_usrp:
	    self.lo_offset = usrp_rate / 2.0
	    print "LO offset set to", self.lo_offset/1e6, "MHz"
	else:
	    self.lo_offset = 0

        
        s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)

        mywindow = filter.window.blackmanharris(self.fft_size)
        ffter = fft.fft_vcc(self.fft_size, True, mywindow, True)
        window_power = sum(map(lambda x: x*x, mywindow))

        c2mag = blocks.complex_to_mag_squared(self.fft_size)

        #Calculate bandwidth & center frequency from start/stop values
	self.bandwidth = self.stop_freq - self.start_freq
	self.center_freq = self.start_freq + round(self.bandwidth/2)

	self.bin2ch_map = [0] * self.fft_size
        hz_per_bin = self.samp_rate / self.fft_size
	channel_bw = hz_per_bin * round(self.bandwidth / self.num_ch / hz_per_bin)
	self.bandwidth = channel_bw * self.num_ch

	for j in range(self.fft_size):
	    fj = self.bin_freq(j, self.center_freq)
	    if (fj >= self.start_freq) and (fj < self.stop_freq):
	        channel_num = int(math.floor((fj - self.start_freq) / channel_bw)) + 1
	        self.bin2ch_map[j] = channel_num
	if self.options.skip_DC:
	    self.bin2ch_map[(self.fft_size + 1) / 2 + 1:] = self.bin2ch_map[(self.fft_size + 1) / 2 : -1]
	    self.bin2ch_map[(self.fft_size + 1) / 2] = 0
	if self.bandwidth > self.samp_rate:
	    print "Warning: Width of band (" + str(self.bandwidth/1e6), "MHz) is greater than the sample rate (" + str(self.samp_rate/1e6), "MHz)."

	self.aggr = myblocks.bin_aggregator_ff(self.fft_size, self.num_ch, self.bin2ch_map)

        meas_frames = max(1, int(round(self.meas_interval * self.samp_rate / self.fft_size))) # in fft_frames
	self.meas_duration = meas_frames * self.fft_size / self.samp_rate
	print "Actual measurement duration =", self.meas_duration, "s"

	self.det_type = self.options.det_type
	det = 0 if self.det_type=='avg' else 1
        self.stats = myblocks.bin_statistics_ff(self.num_ch, meas_frames, det)

	# Divide magnitude-square by a constant to obtain power
	# in Watts.  Assumes unit of USRP source is volts.
	impedance = self.options.impedance   # ohms
	#impedance = 50.0   # ohms
	Vsq2W_dB = -10.0 * math.log10(self.fft_size * window_power * impedance)

	# Convert from Watts to dBm.
	W2dBm = blocks.nlog10_ff(10, self.num_ch, 30 + Vsq2W_dB)

	f2c = blocks.float_to_char(self.num_ch, 1.0)
        g = self.u.get_gain_range()
        if self.options.gain is None:
            # if no gain was specified, use the mid-point in dB
            self.options.gain = float(g.start()+g.stop())/2.0

	# TODO -- fix
        #self.set_gain(options.gain)
        print "gain =", self.options.gain, "dB in range (%0.1f dB, %0.1f dB)" % (float(g.start()), float(g.stop()))
	self.atten = float(g.stop()) - self.options.gain
	self.set_gain(self.options.gain)

	
        delta = long(round(getLocalUtcTimeStamp() - time.time()))
	print "delta = ",delta

        capture_sink = myblocks.capture_sink(itemsize=gr.sizeof_gr_complex, chunksize = 500, capture_dir="/tmp", mongodb_port=self.mongodb_port,\
		event_url="https://" + self.dest_host + ":" + str(443) +  "/eventstream/postCaptureEvent", time_offset = delta)
	
	self.initialize_message_headers()
	capture_sink.set_event_message(str(json.dumps(self.event_msg)))
	trigger = myblocks.dummy_capture_trigger(itemsize=gr.sizeof_gr_complex)
	# Note: pass the trigger here so the trigger can be armed.
	self.sslsocket_sink = myblocks.sslsocket_sink(numpy.int8, self.num_ch,self.dest_host,self.port,self.sys_msg,self.loc_msg,self.data_msg,capture_sink,trigger,self,os.getpid())

	if usrp_rate > self.samp_rate:
	    self.connect(self.u, resamp, s2v)
	    self.flow_graph_1 = [resamp,s2v]
	else:
	    self.connect(self.u, s2v)
	    self.flow_graph_1 = [s2v]

	# Connect the blocks together.
	self.connect(s2v, ffter, c2mag, self.aggr, self.stats, W2dBm, f2c, self.sslsocket_sink)
	self.flow_graph_1 = self.flow_graph_1 + [ffter,c2mag,self.aggr,self.stats,W2dBm,f2c,self.sslsocket_sink]
	# Second pipeline to the sink.
	self.connect(self.u,trigger,capture_sink)
	self.flow_graph_2 = [trigger,capture_sink]
	self.msg_connect(trigger,"trigger",capture_sink,"capture")
	self.connect(self.u,self.scope)


    def __init__(self,frame, panel, vbox, argv):
        global osmo
        global options
        global args
        stdgui2.std_top_block.__init__(self, frame, panel, vbox, argv)
	print "osmo = ",osmo
        self.session = requests.Session()
        self.session.mount('https://', MyAdapter())
        gr.top_block.__init__(self)
        self.flow_graph_1 = None
	self.flow_graph_2 = None
	self.options = options
	self.u = osmo
        self.frame = frame
        self.panel = panel

        if len(args) != 0:
            #parser.print_help()
            print "Please do not add Center Frequency or bandwidth (previously required values).  They are read from the server and values here are not used."
            sys.exit(1)
	#self.frame = frame
	self.dest_host = options.dest_host
	self.samp_rate = options.samp_rate
        self.fft_size = options.fft_size
	self.sensorId = options.sensorId
	self.det_type = options.det_type
	self.mongodb_port = options.mongod_port
	self.init_flow_graph()

    def disconnect_me(self):
	self.lock()
	self.stop()
	self.sslsocket_sink.disconnect()
        try:
           self.u.get_sample_rates().stop()
        except RuntimeError:
	   traceback.print_exc()
           print "Source has no sample rates (wrong device arguments?)."
           sys.exit(1)
	self.disconnect(self.u)
	if self.flow_graph_1 != None:
           print "flow_graph_1: " , str(self.flow_graph_1)
	   apply(self.disconnect,tuple(self.flow_graph_1))
	if self.flow_graph_2 != None:
	   apply(self.disconnect,tuple(self.flow_graph_2))
	self.unlock()

    def reconnect_me(self):
        try:
           self.u.get_sample_rates().start()
        except RuntimeError:
	   traceback.print_exc()
           print "Source has no sample rates (wrong device arguments?)."
           sys.exit(1)
	self.init_flow_graph()

    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        Args:
            target_freq: frequency in Hz
        @rypte: bool
        """
        
	self.u.set_center_freq(target_freq + self.lo_offset)
	freq = self.u.get_center_freq()
        #if hasattr(self.scope, 'set_baseband_freq'):
        #    self.scope.set_baseband_freq(freq)

        if freq == target_freq:
	   return True
	else:
	   return False


    def set_gain(self, gain):
        self.u.set_gain(gain)
    
    def bin_freq(self, i_bin, center_freq):
        hz_per_bin = self.samp_rate / self.fft_size
	# For odd fft_size, treats i_bin = (fft_size + 1) / 2 as the DC bin.
        freq = center_freq + hz_per_bin * (i_bin - self.fft_size / 2 - self.fft_size % 2)
        return freq
    
    def send(self, bytes):
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
    try:
      tb.start()
      tb.wait()
      print "returned from wait"
    except:
	traceback.print_exc()

def start_main_loop():
    time.sleep(3)
    global tb
    signal.signal(signal.SIGUSR1,sigusr1_handler)
    signal.signal(signal.SIGUSR2,sigusr2_handler)
    options,args = parse_options()
    osmo = init_osmosdr(options)
    while True:
       tb = my_top_block(osmo,options,args)
       try:
          main_loop(tb)
       except KeyboardInterrupt:
	   pass

def start_main_loop_gui():
    time.sleep(3)
    global tb,osmo,options,args
    signal.signal(signal.SIGUSR1,sigusr1_handler)
    signal.signal(signal.SIGUSR2,sigusr2_handler)
    options,args = parse_options()

    osmo = init_osmosdr(options)
    while True:
       tb  = stdgui2.stdapp(my_top_block, "osmocom Spectrum Browser", nstatus=1)
       try:
          app.MainLoop()
       except KeyboardInterrupt:
	   pass
    #app = stdgui2.stdapp(my_top_block, "osmocom Spectrum Browser", nstatus=1)
    #try:
    #   app.MainLoop()
    #except KeyboardInterrupt:
    #   pass

       
def sigusr2_handler(signo,frame):
	print "<<<<<<<<< got a signal " + str(signo) 
        global tb
	tb.stop()
	sys.exit(0)
	os._exit(0)

def sigusr1_handler(signo,frame):
        signal.signal(signal.SIGUSR1,sigusr1_handler)
	print "<<<<<<<<< got a signal " + str(signo) 
	if "tb" in globals():
           global tb
	   #tb.stop()
	   tb.disconnect_me()


	
if __name__ == '__main__':
    mychild = Process(target=start_main_loop_gui)
    mychild.start()
    t = ThreadClass()
    t.start()

  
