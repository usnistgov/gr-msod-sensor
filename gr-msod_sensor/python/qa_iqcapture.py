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

class qa_iqcapture (gr_unittest.TestCase):

    def setUp (self):
        self.tb = gr.top_block ()

    def tearDown (self):
        self.tb = None

    def test_001_t (self):
	print "Test capture"
        src_data = (7, 4, 5, 2, 4)
        expected_result= (7, 4, 5, 2, 4)
        src = blocks.vector_source_f(src_data)
        sqr = capture.iqcapture(4)
        dst = blocks.vector_sink_f()
        self.tb.connect(src, sqr)
        self.tb.connect(sqr, dst)
        self.tb.run()
        result_data = dst.data()
        print "result_data", result_data
        self.assertFloatTuplesAlmostEqual(expected_result, result_data, 4)

        # set up fg
        #self.tb.run ()
        # check data


if __name__ == '__main__':
    gr_unittest.run(qa_iqcapture, "qa_iqcapture.xml")
