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

class qa_capture_sink (gr_unittest.TestCase):

    def setUp (self):
	for file in os.listdir("/tmp"):
    		if file.startswith("capture"):
			os.remove("/tmp/" + file)
        self.tb = gr.top_block ()
	self.u = blocks.file_source(gr.sizeof_float,"/tmp/testdata.bin",False)
	self.throttle = blocks.throttle(itemsize=gr.sizeof_float,samples_per_sec=1000)
	self.tb.connect(self.u,self.throttle)
        self.sqr = capture.capture_sink(itemsize=gr.sizeof_float, chunksize = 500, capture_dir="/tmp")
	self.tb.connect(self.throttle,self.sqr)
	size = 0

    def tearDown (self):
        self.tb = None
	for file in os.listdir("/tmp"):
    		if file.startswith("capture"):
			os.remove("/tmp/" + file)

    def test_001_t (self):
	print "test_001_t"
	self.sqr.start_capture()
        self.tb.run ()
	size = 0
	for file in os.listdir("/tmp"):
    		if file.startswith("capture"):
			stat = os.stat("/tmp/" + file)
			size = size + stat.st_size 
	original_file_size = os.stat("/tmp/testdata.bin").st_size
	print "original file size ", original_file_size, " capture file size ", size
	self.assertEquals(size,original_file_size)
        # check data TBD

    def test_002_t (self):
	self.sqr.stop_capture()
        self.tb.run ()
	for file in os.listdir("/tmp"):
    		if file.startswith("capture"):
			self.fail("File should not exist")


if __name__ == '__main__':
    gr_unittest.run(qa_capture_sink, "qa_capture_sink.xml")
