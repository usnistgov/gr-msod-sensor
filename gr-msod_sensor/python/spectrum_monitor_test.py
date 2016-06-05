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
import msod_sensor
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

currentDir = os.getcwd()
sys.path.append(currentDir + "/gr-msod_sensor/python")
from timezone import getLocalUtcTimeStamp, formatTimeStampLong


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
        parser.add_option("-s",
                          "--samp-rate",
                          type="eng_float",
                          default=1e6,
                          help="set sample rate [default=%default]")
        parser.add_option(
            "-t",
            "--det-type",
            type="string",
            default="avg",
            help="set detection type ('avg' or 'peak') [default=%default]")
        parser.add_option(
            "-c",
            "--number-channels",
            type="int",
            default=100,
            help="number of uniform channels for which to report power measurements [default=%default]")
        parser.add_option("-F",
                          "--fft-size",
                          type="int",
                          default=1024,
                          help="specify number of FFT bins [default=%default]")
        parser.add_option("",
                          "--real-time",
                          action="store_true",
                          default=False,
                          help="Attempt to enable real-time scheduling")
        parser.add_option("-d",
                          "--dest-host",
                          type="string",
                          default="",
                          help="set destination host for streaming data")
        parser.add_option(
            "",
            "--skip-DC",
            action="store_true",
            default=False,
            help="skip the DC bin when mapping channels, [default = %default]")
        parser.add_option(
            "",
            "--meas-interval",
            type="eng_float",
            default=0.1,
            metavar="SECS",
            help="interval over which to measure statistic (in seconds) [default=%default]")

        (options, args) = parser.parse_args()
        print "options ", options, " args ", args
        if len(args) != 2:
            parser.print_help()
            print "len(args) ", len(args)
            sys.exit(1)

        self.center_freq = eng_notation.str_to_num(args[0])
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
        self.u = blocks.file_source(gr.sizeof_gr_complex, "/tmp/testdata.bin",
                                    True)

        print "samp_rate ", options.samp_rate

        self.throttle = blocks.throttle(
            itemsize=gr.sizeof_gr_complex,
            samples_per_sec=float(options.samp_rate))

        self.connect(self.u, self.throttle)

        self.samp_rate = options.samp_rate

        self.fft_size = options.fft_size
        self.num_ch = options.number_channels

        s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)

        mywindow = filter.window.blackmanharris(self.fft_size)
        ffter = fft.fft_vcc(self.fft_size, True, mywindow, True)
        window_power = sum(map(lambda x: x * x, mywindow))

        c2mag = blocks.complex_to_mag_squared(self.fft_size)

        self.bin2ch_map = [0] * self.fft_size
        hz_per_bin = self.samp_rate / self.fft_size
        channel_bw = hz_per_bin * round(self.bandwidth / self.num_ch /
                                        hz_per_bin)
        self.bandwidth = channel_bw * self.num_ch
        print "Actual width of band is", self.bandwidth / 1e6, "MHz."
        start_freq = self.center_freq - self.bandwidth / 2.0
        stop_freq = start_freq + self.bandwidth
        for j in range(self.fft_size):
            fj = self.bin_freq(j, self.center_freq)
            if (fj >= start_freq) and (fj < stop_freq):
                channel_num = int(math.floor((fj - start_freq) /
                                             channel_bw)) + 1
                self.bin2ch_map[j] = channel_num
        if options.skip_DC:
            self.bin2ch_map[(self.fft_size + 1) / 2 + 1:] = self.bin2ch_map[(
                self.fft_size + 1) / 2:-1]
            self.bin2ch_map[(self.fft_size + 1) / 2] = 0
        if self.bandwidth > self.samp_rate:
            print "Warning: Width of band (" + str(
                self.bandwidth /
                1e6), "MHz) is greater than the sample rate (" + str(
                    self.samp_rate / 1e6), "MHz)."

        self.aggr = msod_sensor.bin_aggregator_ff(self.fft_size, self.num_ch,
                                                  self.bin2ch_map)

        meas_frames = max(1, int(round(options.meas_interval * self.samp_rate /
                                       self.fft_size)))  # in fft_frames
        self.meas_duration = meas_frames * self.fft_size / self.samp_rate
        print "Actual measurement duration =", self.meas_duration, "s"

        self.det_type = options.det_type
        det = 0 if self.det_type == 'avg' else 1
        self.stats = msod_sensor.bin_statistics_ff(self.num_ch, meas_frames,
                                                   det)

        # Divide magnitude-square by a constant to obtain power
        # in Watts.  Assumes unit of USRP source is volts.
        impedance = 50.0  # ohms
        Vsq2W_dB = -10.0 * math.log10(self.fft_size * window_power * impedance)

        # Convert from Watts to dBm.
        W2dBm = blocks.nlog10_ff(10.0, self.num_ch, 30.0 + Vsq2W_dB)

        f2c = blocks.float_to_char(self.num_ch, 1.0)

        self.dest_host = options.dest_host

        # ssl socket is set in main loop; use dummy value for now
        self.srvr = msod_sensor.sslsocket_sink(numpy.int8, self.num_ch, 0)

        self.capture = msod_sensor.iqcapture_sink(gr.sizeof_gr_complex,
                                                  chunksize=5000,
                                                  "/tmp",
                                                  mongodb_port=3000)
        self.connect(self.throttle, s2v)
        self.connect(self.throttle, self.capture)
        self.connect(s2v, ffter, c2mag, self.aggr, self.stats, W2dBm, f2c,
                     self.srvr)
        #self.connect(s2v, ffter, c2mag, self.aggr, self.stats, W2dBm, self.srvr)
        self.atten = -3

    def bin_freq(self, i_bin, center_freq):
        hz_per_bin = self.samp_rate / self.fft_size
        # For odd fft_size, treats i_bin = (fft_size + 1) / 2 as the DC bin.
        freq = center_freq + hz_per_bin * (i_bin - self.fft_size / 2 -
                                           self.fft_size % 2)
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
        f = open(fname, 'r')
        obj = json.load(f)
        f.close()
        return obj


def main_loop(tb):

    sensor_id = "TestSensor"
    r = requests.post('https://' + tb.dest_host +
                      '/sensordata/getStreamingPort/' + sensor_id,
                      verify=False)
    print 'server response:', r.text
    response = r.json()
    print 'socket port =', response['port']
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tb.s = s = ssl.wrap_socket(sock)
    s.connect((tb.dest_host, response['port']))
    tb.set_sock(s)

    # Send location and system info to server
    loc_msg = tb.read_json_from_file('sensor.loc')
    loc_msg["SensorID"] = sensor_id
    sys_msg = tb.read_json_from_file('sensor.sys')
    sys_msg["SensorID"] = sensor_id
    ts = long(round(getLocalUtcTimeStamp()))
    print 'Serial no.', sensor_id
    loc_msg['t'] = ts
    loc_msg['SensorID'] = sensor_id
    sys_msg['t'] = ts
    sys_msg['SensorID'] = sensor_id
    tb.send_obj(loc_msg)
    tb.send_obj(sys_msg)

    # Form data header
    ts = long(round(getLocalUtcTimeStamp()))
    f_start = tb.center_freq - tb.bandwidth / 2.0
    f_stop = f_start + tb.bandwidth
    # Note -- dummy atten
    mpar = Struct(fStart=f_start,
                  fStop=f_stop,
                  n=tb.num_ch,
                  td=-1,
                  tm=tb.meas_duration,
                  Det='Average' if tb.det_type == 'avg' else 'Peak',
                  Atten=tb.atten)
    # Need to add a field for overflow indicator
    data = Struct(Ver='1.0.12', Type='Data', SensorID=sensor_id, SensorKey='NaN', t=ts, Sys2Detect='LTE', \
 Sensitivity='Low', mType='FFT-Power', t1=ts, a=1, nM=-1, Ta=-1, OL='NaN', wnI=-77.0, \
 Comment='Using hard-coded (not detected) system noise power for wnI', \
 Processed='False', DataType = 'Binary - int8', ByteOrder='N/A', Compression='None', mPar=mpar)

    tb.send_obj(data)
    date_str = formatTimeStampLong(ts, loc_msg['TimeZone'])
    print date_str, "fc =", tb.center_freq / 1e6, "MHz. Sending data to", tb.dest_host

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
