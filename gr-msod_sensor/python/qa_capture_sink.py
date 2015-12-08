#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2015 <+YOU OR YOUR COMPANY+>.
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr, gr_unittest
from gnuradio import blocks
import msod_sensor_swig as capture
import os
import json
import time
import pymongo
global mongoclient

global MONGODB_PORT 

MONGODB_PORT=33000

class Struct(dict):
    def __init__(self, **kwargs):
	super(Struct, self).__init__(**kwargs)
	self.__dict__ = self

def generate_data_message():
    f_start = 703990000
    f_stop  = 714994000
    num_ch = 56
    atten = 30
    meas_duration = 100
    sensor_id = "TestSensor"
    mpar = Struct(fStart=f_start, fStop=f_stop, n=num_ch, td=-1, tm=meas_duration, Det='Peak', Atten=atten)
    # Need to add a field for overflow indicator
    ts = int(time.time())
    data = Struct(Ver='1.0.12', Type='Data', SensorID=sensor_id, SensorKey='NaN', t=ts, Sys2Detect='LTE', \
	Sensitivity='Low', mType='FFT-Power', t1=ts, a=1, nM=-1, Ta=-1, OL='NaN', wnI=-77.0, \
	Comment='Using hard-coded (not detected) system noise power for wnI', \
	Processed='False', DataType = 'Binary - int8', ByteOrder='N/A', Compression='None', mPar=mpar)
    return json.dumps(data)


class qa_capture_sink (gr_unittest.TestCase):

    def setUp (self):
	for file in os.listdir("/tmp"):
    		if file.startswith("capture"):
			os.remove("/tmp/" + file)
	metadata = mongoclient.iqcapture.dataMessages.remove({"SensorID":"TestSensor"})
        self.tb = gr.top_block ()
	self.u = blocks.file_source(gr.sizeof_float,"/tmp/testdata.bin",False)
	self.throttle = blocks.throttle(itemsize=gr.sizeof_float,samples_per_sec=1000)
	self.tb.connect(self.u,self.throttle)
	self.chunksize = 500
	self.itemsize = gr.sizeof_float
        self.sqr = capture.capture_sink(itemsize=self.itemsize, chunksize = self.chunksize, capture_dir="/tmp", mongodb_port=MONGODB_PORT)
	self.tb.connect(self.throttle,self.sqr)

    def tearDown (self):
        self.tb = None
	for file in os.listdir("/tmp"):
    		if file.startswith("capture"):
			os.remove("/tmp/" + file)

    def test_001_t (self):
	print "test_001_t"
	initialCount = 0
	self.sqr.set_data_message(generate_data_message())
	self.sqr.start_capture()
        self.tb.run ()
	size = 0
	count = 0
	for file in os.listdir("/tmp"):
    		if file.startswith("capture"):
			print file
			stat = os.stat("/tmp/" + file)
			size = size + stat.st_size 
			count = count + 1
	self.assertEquals(count,1)
	original_file_size = os.stat("/tmp/testdata.bin").st_size
	print "original file size ", original_file_size, " capture file size ", size, " count ", count
	self.assertEquals(size,self.chunksize * self.itemsize)
        # check data TBD
	metadata = mongoclient.iqcapture.dataMessages.find({"SensorID":"TestSensor"})
	print "metadata count ", metadata.count()
	self.assertEquals(metadata.count(),count)
	

    def test_002_t (self):
	self.sqr.stop_capture()
        self.tb.run ()
	for file in os.listdir("/tmp"):
    		if file.startswith("capture"):
			self.fail("File should not exist")


if __name__ == '__main__':
    global mongoclient
    global MONGODB_PORT
    mongoclient = pymongo.MongoClient("127.0.0.1",MONGODB_PORT)
    mongoclient.iqcapture.dataMessages.drop()
    gr_unittest.run(qa_capture_sink, "qa_capture_sink.xml")
