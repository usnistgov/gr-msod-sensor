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
import os
import json
import time
import pymongo
global mongoclient
import msod_sensor_swig as capture


class Struct(dict):
    def __init__(self, **kwargs):
        super(Struct, self).__init__(**kwargs)
        self.__dict__ = self


def generate_data_message():
    f_start = 703990000
    f_stop = 714994000
    num_ch = 56
    atten = 30
    meas_duration = 100
    sensor_id = "TestSensor"
    mpar = Struct(fStart=f_start,
                  fStop=f_stop,
                  n=num_ch,
                  td=-1,
                  tm=meas_duration,
                  Det='Peak',
                  Atten=atten)
    # Need to add a field for overflow indicator
    ts = int(time.time())
    data = Struct(Ver='1.0.12', Type='Data', SensorID=sensor_id, SensorKey='NaN', t=ts, Sys2Detect='LTE', \
 Sensitivity='Low', mType='FFT-Power', t1=ts, a=1, nM=-1, Ta=-1, OL='NaN', wnI=-77.0, \
 Comment='Using hard-coded (not detected) system noise power for wnI', \
 Processed='False', DataType = 'Binary - int8', ByteOrder='N/A', Compression='None', mPar=mpar)
    return json.dumps(data)


class qa_iqcapture_sink(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()
        for file in os.listdir("/tmp"):
            if file.startswith("iqcapture"):
                os.remove("/tmp/" + file)
        self.tb = gr.top_block()
        self.u = blocks.file_source(gr.sizeof_float, "/tmp/testdata.bin",
                                    False)
        self.throttle = blocks.throttle(itemsize=gr.sizeof_float,
                                        samples_per_sec=1000)
        self.tb.connect(self.u, self.throttle)
        self.sqr = capture.iqcapture_sink(itemsize=gr.sizeof_float,
                                          chunksize=500,
                                          capture_dir="/tmp",
                                          mongodb_port=33000)
        self.tb.connect(self.throttle, self.sqr)

    def tearDown(self):
        self.tb = None

    def test_001_t(self):
        # set up fg
        self.tb.run()
        # check data


if __name__ == '__main__':
    gr_unittest.run(qa_iqcapture_sink, "qa_iqcapture_sink.xml")
