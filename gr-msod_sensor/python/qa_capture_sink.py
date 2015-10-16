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
        sqr = capture.capture_sink(itemsize=gr.sizeof_float, chunksize = 500, capture_dir="/tmp")
	sqr.start_capture()
	self.tb.connect(self.throttle,sqr)

    def tearDown (self):
        self.tb = None

    def test_001_t (self):
        self.tb.run ()
        # check data TBD


if __name__ == '__main__':
    gr_unittest.run(qa_capture_sink, "qa_capture_sink.xml")
