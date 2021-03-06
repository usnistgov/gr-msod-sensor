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

from __future__ import print_function

from gnuradio import gr
from gnuradio import blocks
from gnuradio import filter
from gnuradio import fft
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math
import msod_sensor as myblocks
import time
import json
import ssl
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import numpy
import os
import signal
import traceback
from multiprocessing import Process

from msod_sensor import forensics

try:
    import osmosdr
    HAVE_OSMOSDR = True
except ImportError:
    HAVE_OSMOSDR = False


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


def parse_options():
    usage = "usage: %prog [options]"  # center_freq band_width"
    parser = OptionParser(option_class=eng_option, usage=usage)
    parser.add_option("-a",
                      "--args",
                      type="string",
                      default="",
                      help="Device address args [default=%default]")
    parser.add_option("",
                      "--spec",
                      type="string",
                      default=None,
                      help="Subdevice of UHD device where appropriate")
    parser.add_option("-A",
                      "--antenna",
                      type="string",
                      default=None,
                      help="select Rx Antenna where appropriate")
    parser.add_option("-g",
                      "--gain",
                      type="eng_float",
                      default=None,
                      help="set gain in dB (default is midpoint)")
    parser.add_option("-l",
                      "--lo-offset",
                      type="eng_float",
                      default=None,
                      metavar="Hz",
                      help="lo-offset in Hz [default=half the sample rate]")
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
    parser.add_option("",
                      "--skip-DC",
                      action="store_true",
                      default=False,
                      help="skip the DC bin when mapping channels")
    parser.add_option("-S",
                      "--sensorId",
                      type="string",
                      default=None,
                      help="Sensor ID -- required must be unique")
    parser.add_option("-k",
                      "--sensorKey",
                      type="string",
                      default=None,
                      help="Sensor Key -- required")
    parser.add_option("-m",
                      "--mongod-port",
                      type="int",
                      default=2017,
                      help="Mongodb port")
    parser.add_option("",
                      "--latitude",
                      type="float",
                      help="latitude")

    parser.add_option("",
                      "--longitude",
                      type="float",
                      help="longitude")

    #parser.add_option("",
    #                  "--fft-rate",
    #                  type="int",
    #                  default=30,
    #                  help="Set FFT update rate, [default=%default]")
    parser.add_option("",
                      "--capture-duration",
                      type="eng_float",
                      default=3.0,
                      help="I/Q capture duration (s), default = [%default]")
    parser.add_option("",
                      "--power-offset",
                      type="eng_float",
                      default=1,
                      help="Additive power offset for calibration " +
                           "(linear NOT dB). default = [%default] ")
    parser.add_option("",
                      "--if-gain",
                      type="eng_float",
                      default=22,
                      help="IF gain for OSMO SDR. default = [%default] ")
    parser.add_option("",
                      "--source",
                      type="string",
                      default=None,
                      help="source type -- file,uhd or osmo. ")
    parser.add_option("",
                      "--analyze",
                      type="string",
                      default=None,
                      help="path to the analysis script. default = None")

    (options, args) = parser.parse_args()
    return options, args


def init_file_source(options):
    args = options.args
    fileName = str.split(args, "=")[1]
    file_source = blocks.file_source(itemsize=gr.sizeof_gr_complex,
                                     filename=fileName,
                                     repeat=True)
    return file_source


def init_osmosdr(options, config):
    print("init_osmosdr ", end='')
    print(json.dumps(config, indent=4))
    activeBands = config["thresholds"]
    for band in activeBands.values():
        if band["active"]:
            samp_rate = band["samplingRate"]
            break
    u = osmosdr.source(args=options.args)
    u.set_freq_corr(0, 0)
    u.set_dc_offset_mode(1, 0)
    u.set_dc_offset(0, 0)
    u.set_iq_balance_mode(0, 0)
    u.set_gain_mode(True, 0)
    if options.gain is not None:
        u.set_gain(options.gain, 0)
    u.set_if_gain(options.if_gain, 0)
    u.set_bb_gain(0, 0)
    # Walk through the sample rates of the device and pick
    u.set_sample_rate(samp_rate)
    # Set the antenna
    if (options.antenna):
        u.set_antenna(self.options.antenna)
    if u.get_sample_rate() != samp_rate:
        sample_rate_set = False
        for p in u.get_sample_rates():
            if p.start() >= samp_rate:
                print("sample_rates size {}".format(
                    u.get_sample_rates().size()))
                sample_rate_set = True
                u.set_sample_rate(float(p.start()))
                break
        if not sample_rate_set:
            print("Cannot set sample rate - exiting")
            sys.exit(0)
            os._exit(0)

    rate = u.get_sample_rate()
    if samp_rate != rate:
        print("rate mismatch -- inserting fractional resampler")
        resamp = filter.fractional_resampler_cc(0.0,
                                                usrp_rate / self.samp_rate)
    else:
        resamp = None
    try:
        u.get_sample_rates().start()
    except RuntimeError:
        traceback.print_exc()
        print("Source has no sample rates (wrong device arguments?).")
        sys.exit(1)
        os._exit(0)

    return u, resamp


def init_uhd(options, config):
    print("init_uhd ", end='')
    print(json.dumps(config, indent=4))
    activeBands = config["thresholds"]
    samp_rate = None

    for band in activeBands.values():
        if band["active"]:
            samp_rate = band["samplingRate"]
            break

    if samp_rate is None:
        print("Could not find an active band -- check server configuration.")
        sys.exit(0)
        os._exit(0)

    u = uhd.usrp_source(device_addr=options.args,
                        stream_args=uhd.stream_args('fc32'))

    # Set the subdevice spec
    if options.spec:
        self.u.set_subdev_spec(options.spec, 0)

    # Set the antenna
    if (options.antenna):
        self.u.set_antenna(options.antenna, 0)

    clock_rate = samp_rate if samp_rate >= 10e6 else 4 * samp_rate

    # If radio doesn't have adjustable master clock, this should be no-op.
    u.set_clock_rate(clock_rate)
    clock_rate = int(u.get_clock_rate())

    print("init_uhd: setting sample rate to {}".format(samp_rate))
    u.set_samp_rate(samp_rate)
    usrp_rate = int(u.get_samp_rate())

    if usrp_rate != samp_rate:
        if usrp_rate < samp_rate:
            # create list of allowable rates
            samp_rates = u.get_samp_rates()
            rate_list = [0.0] * len(samp_rates)
            for i in range(len(rate_list)):
                last_rate = samp_rates.pop()
                rate_list[len(rate_list) - 1 - i] = last_rate.start()
            # choose next higher rate
            rate_ind = rate_list.index(usrp_rate) + 1
            if rate_ind < len(rate_list):
                u.set_samp_rate(rate_list[rate_ind])
                usrp_rate = u.get_samp_rate()
            print("New actual sample rate = {} MHz".format(usrp_rate / 1e6))
        resamp = filter.fractional_resampler_cc(0.0, usrp_rate / samp_rate)
    else:
        resamp = None

    u.start()
    return u, resamp


class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_SSLv23)


def read_configuration(sensor_id, dest_host, latitude, longitude):
    print('host: {}'.format(dest_host))
    streaming_url = 'https://{}:443/sensordata/getStreamingPort/{}'
    streaming_url = streaming_url.format(dest_host, sensor_id)
    print('Requesting streaming port from {}'.format(streaming_url))
    r = requests.post(streaming_url, verify=False)
    location = {}
    js = r.json()
    port = js["port"]
    print('socket port = {}'.format(port))
    config_url = 'https://{}:443/sensordb/getSensorConfig/{}'
    config_url = config_url.format(dest_host, sensor_id)
    print('Requesting sensor config from {}'.format(config_url))
    location["timestamp"] = time.time()
    location["latitude"] = latitude
    location["longitude"] = longitude
    r = requests.post(config_url, data=str(json.dumps(location)), verify=False)
    #print('server response: ' + r.text)
    js = r.json()
    return js["sensorConfig"], port, js["timeOffset"]


class my_top_block(gr.top_block):
    def init_config(self, config):
        """
        Initialize the configuration based on what was read from the server.
        """
        self.det_type = config["streaming"]["streamingFilter"]
        self.meas_interval = config["streaming"]["streamingSecondsPerFrame"]
        activeBands = config["thresholds"]
        for band in activeBands.values():
            if band["active"]:
                self.start_freq = band["minFreqHz"]
                self.stop_freq = band["maxFreqHz"]
                self.num_ch = band["channelCount"]
                self.samp_rate = band["samplingRate"]
                self.fft_size = band["fftSize"]

    def initialize_message_headers(self):
        self.loc_msg = self.read_json_from_file('sensor.loc')
        self.sys_msg = self.read_json_from_file('sensor.sys')
        self.data_msg = self.read_json_from_file('sensor.data')
        self.event_msg = self.read_json_from_file('sensor.event')
        ts =  time.time() + self.delta
        self.loc_msg['t'] = ts
        self.loc_msg['SensorID'] = self.sensorId
        self.loc_msg['SensorKey'] = self.sensorKey
        self.sys_msg['t'] = ts
        self.sys_msg['SensorID'] = self.sensorId
        self.sys_msg['SensorKey'] = self.sensorKey
        self.data_msg['t'] = ts
        self.data_msg['t1'] = ts
        # Fix up the data message in accordance with various input parameters.
        det = 'Mean' if self.det_type == 'MEAN' else 'Peak'
        self.data_msg['SensorID'] = self.sensorId
        self.data_msg['SensorKey'] = self.sensorKey
        # conver to float to avoid confusing the C++ JSON library
        self.data_msg['mPar']['fStart'] = float(self.start_freq)
        self.data_msg['mPar']['fStop'] = float(self.stop_freq)
        self.data_msg['mPar']['Atten'] = self.atten
        self.data_msg['mPar']['Det'] = det
        self.data_msg['mPar']['tm'] = self.meas_interval
        self.data_msg['mPar']['n'] = self.num_ch

        self.event_msg['SensorID'] = self.sensorId
        self.event_msg['SensorKey'] = self.sensorKey
        self.event_msg['mPar']['fStart'] = float(self.start_freq)
        self.event_msg['mPar']['fStop'] = float(self.stop_freq)
        self.event_msg['mPar']['Atten'] = self.atten
        self.event_msg['mPar']['n'] = self.num_ch
        self.event_msg['mPar']['sampRate'] = self.get_sample_rate()

    def init_flow_graph(self):
        if self.options.real_time:
            r = gr.enable_realtime_scheduling()
            if r != gr.RT_OK:
                print("Note: failed to enable realtime scheduling")

        if self.options.args:
            self.use_usrp = self.options.args.startswith("uhd")
            self.file_source = self.options.args.startswith("file")
        else:
            self.use_usrp = self.file_source = False

        if self.options.lo_offset is not None:
            self.lo_offset = self.options.lo_offset
            print("LO offset set to {} MHz".format(self.lo_offset / 1e6))
        else:
            self.lo_offset = 0

        # Calibrate dBm (add self.options.power_offset)
        power_cal = blocks.multiply_const_cc(self.options.power_offset)
        s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)

        mywindow = filter.window.blackmanharris(self.fft_size)
        ffter = fft.fft_vcc(self.fft_size, True, mywindow, True)
        window_power = sum(map(lambda x: x * x, mywindow))

        c2mag = blocks.complex_to_mag_squared(self.fft_size)

        # Calculate bandwidth & center frequency from start/stop values
        self.bandwidth = self.stop_freq - self.start_freq
        self.center_freq = self.start_freq + round(self.bandwidth / 2)
        print("self.center_freq {} ".format(self.center_freq))

        self.bin2ch_map = [0] * self.fft_size
        hz_per_bin = float(self.samp_rate) / self.fft_size
        channel_bw = hz_per_bin * round(self.bandwidth / self.num_ch /
                                        hz_per_bin)
        self.bandwidth = channel_bw * self.num_ch

        for j in range(self.fft_size):
            fj = self.bin_freq(j, self.center_freq)
            if (fj >= self.start_freq) and (fj < self.stop_freq):
                channel_num = int(math.floor((fj - self.start_freq) /
                                             channel_bw)) + 1
                self.bin2ch_map[j] = channel_num
        if self.options.skip_DC:
            self.bin2ch_map[(self.fft_size + 1) / 2 + 1:] = self.bin2ch_map[(
                self.fft_size + 1) / 2:-1]
            self.bin2ch_map[(self.fft_size + 1) / 2] = 0
        if self.bandwidth > self.samp_rate:
            wrn = "Warning: Width of band ({} MHz) "
            wrn += "is greater than sample rate ({} MHz)"
            print(wrn.format(self.bandwidth / 1e6, self.samp_rate / 1e6))

        self.aggr = myblocks.bin_aggregator_ff(self.fft_size, self.num_ch,
                                               self.bin2ch_map)

        meas_frames = max(1, int(round(self.meas_interval * self.samp_rate /
                                       self.fft_size)))  # in fft_frames
        self.meas_duration = meas_frames * self.fft_size / self.samp_rate
        print("Actual measurement duration = {} s".format(self.meas_duration))

        det = 0 if self.det_type == "MEAN" else 1
        self.stats = myblocks.bin_statistics_ff(self.num_ch, meas_frames, det)

        # Divide magnitude-square by a constant to obtain power
        # in Watts.  Assumes unit of USRP source is volts.
        impedance = 50.0   # ohms
        Vsq2W_dB = -10.0 * math.log10(self.fft_size * window_power * impedance)

        # Convert from Watts to dBm. 0dBW = 30dBm, so +30
        W2dBm = blocks.nlog10_ff(10, self.num_ch, Vsq2W_dB + 30)

        f2c = blocks.float_to_char(self.num_ch, 1.0)
        if not self.options.source == "file":
            g = self.u.get_gain_range()
            if self.options.gain is None:
                # if no gain was specified, use the mid-point in dB
                self.options.gain = float(g.start() + g.stop()) / 2.0

            # TODO -- fix
            #self.set_gain(options.gain)
            print("gain = {} dB in range ({:0.1f} dB, {:0.1f} dB)".format(
                self.options.gain, float(g.start()), float(g.stop())))
            self.atten = float(g.stop()) - self.options.gain
        else:
            self.atten = 0

        self.set_gain(self.options.gain)

        print("time delta = {}".format(self.delta))

        chunksize = int(self.get_sample_rate() * self.options.capture_duration)
        srate = int(self.get_sample_rate())
        event_url = 'https://{}:443/eventstream/postCaptureEvent'
        event_url = event_url.format(self.dest_host)
        capture_sink = myblocks.capture_sink(itemsize=gr.sizeof_gr_complex,
                                             chunksize=chunksize,
                                             samp_rate=srate,
                                             capture_dir="/tmp",
                                             mongodb_port=self.mongodb_port,
                                             event_url=event_url,
                                             time_offset=self.delta)

        self.initialize_message_headers()
        print(json.dumps(self.event_msg, indent=4))
        capture_sink.set_event_message(str(json.dumps(self.event_msg)))

        trigger = myblocks.level_capture_trigger(itemsize=gr.sizeof_gr_complex,
                                                 level=-40,
                                                 window_size=1024)
        # Note: pass the trigger here so the trigger can be armed.
        self.sslsocket_sink = myblocks.sslsocket_sink(numpy.int8,
                                                      self.sensorId,
                                                      self.num_ch,
                                                      self.dest_host,
                                                      self.port,
                                                      self.sys_msg,
                                                      self.loc_msg,
                                                      self.data_msg,
                                                      trigger,
                                                      self,
                                                      os.getpid())

        if self.resamp:
            self.connect(self.u, self.resamp, power_cal)
            self.flow_graph_1 = [self.resamp, power_cal]
        else:
            self.connect(self.u, power_cal)
            self.flow_graph_1 = [power_cal]

        self.skip = blocks.skiphead(gr.sizeof_float * self.fft_size, 10)
        self.head = blocks.head(gr.sizeof_float * self.fft_size, 1)
        self.vsink = blocks.vector_sink_f(1024)

        # Connect the blocks together.
        self.connect(power_cal, s2v, ffter, c2mag, self.aggr, self.stats,
                     W2dBm, f2c, self.sslsocket_sink)
        self.flow_graph_1.append([ffter, c2mag, self.stats, W2dBm,
                                  f2c, self.sslsocket_sink])

        # Second pipeline to the sink.
        self.connect(self.u, trigger, capture_sink)
        # record the configuration.
        self.flow_graph_2 = [trigger, capture_sink]
        self.msg_connect(trigger, "trigger", capture_sink, "capture")

    def is_file_source(self):
        return self.options.source == "file"

    def __init__(self, source, resamp, options, config, port, delta):
        print("source = {}".format(source))
        print("options = {}".format(options))
        self.delta = delta
        self.init_config(config)
        self.port = port
        self.session = requests.Session()
        self.session.mount('https://', MyAdapter())
        gr.top_block.__init__(self)
        self.flow_graph_1 = None
        self.flow_graph_2 = None
        self.options = options
        self.resamp = resamp
        if not self.is_file_source():
            self.u = source
        else:
            print("samp_rate = {}".format(self.samp_rate))
            u = blocks.throttle(itemsize=gr.sizeof_gr_complex,
                                samples_per_sec=4 * self.samp_rate)
            self.connect(source, u)
            self.u = u

        self.dest_host = options.dest_host
        self.sensorId = options.sensorId
        self.sensorKey = options.sensorKey
        self.det_type = config["streaming"]["streamingFilter"]
        self.mongodb_port = options.mongod_port
        self.init_flow_graph()

    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        Args:
            target_freq: frequency in Hz
        @rypte: bool
        """

        if self.options.source == "osmo":
            print("set_freq: target_freq = {}".format(target_freq))
            self.u.set_center_freq(target_freq)
            freq = self.u.get_center_freq()
            self.center_freq = freq
            if freq == target_freq:
                return True
            else:
                print("actual freq  = {}".format(freq))
            return False
        elif self.options.source == "uhd":
            r = self.u.set_center_freq(uhd.tune_request(
                target_freq,
                rf_freq=(target_freq + self.lo_offset),
                rf_freq_policy=uhd.tune_request.POLICY_MANUAL))
            if r:
                return True
            else:
                return False

        elif self.options.source == "file":
            self.center_freq = target_freq
            return True
        else:
            print("Unknown source -- exiting")
            sys.exit()
            os._exit(0)

    def set_gain(self, gain):
        if not self.is_file_source():
            self.u.set_gain(gain)
        else:
            self.gain = gain

    def set_sample_rate(self, sample_rate):
        if self.options.source == "file":
            self.samp_rate = sample_rate
        elif self.options.source == "osmo":
            self.u.set_sample_rate(sample_rate)
        else:
            self.u.set_samp_rate(sample_rate)

    def get_sample_rate(self):
        if self.options.source == "file":
            return self.samp_rate
        elif self.options.source == "osmo":
            return self.u.get_sample_rate()
        else:
            return self.u.get_samp_rate()

    def bin_freq(self, i_bin, center_freq):
        hz_per_bin = self.samp_rate / self.fft_size
        # For odd fft_size, treats i_bin = (fft_size + 1) / 2 as the DC bin.
        freq = center_freq + hz_per_bin * (i_bin - self.fft_size /
                                           2 - self.fft_size % 2)
        return freq

    def send(self, bytes):
        self.s.send(bytes)

    def set_bin2ch_map(self, bin2ch_map):
        self.aggr.set_bin_index(bin2ch_map)

    def read_json_from_file(self, fname):
        f = open(fname, 'r')
        print(fname)
        obj = json.load(f)
        f.close()
        return obj


def main_loop(tb):
    print('starting main loop')
    if not tb.set_freq(tb.center_freq):
        print("Failed to set frequency to {}".format(tb.center_freq))
    print("Set frequency to {} MHz".format(tb.center_freq / 1e6))
    time.sleep(0.25)
    # Start flow graph
    try:
        tb.start()
        tb.wait()
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        raise
    except:
        traceback.print_exc()


def start_main_loop():
    global tb
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    signal.signal(signal.SIGUSR2, sigusr2_handler)
    options, args = parse_options()
    config, port, delta = read_configuration(options.sensorId,
                                             options.dest_host,
                                             options.latitude,
                                             options.longitude)
    # Reading form a file?
    if options.source == "osmo":
        source, resamp = init_osmosdr(options, config)
    elif options.source == "uhd":
        source, resamp = init_uhd(options, config)
    elif options.source == "file":
        source = init_file_source(options)
        resamp = None
    else:
        print("Unrecognized options options.source {!r}".format(options.source))
        os._exit(-1)

    if options.analyze is not None:
        scanner = Process(target=forensics.run_forensics,
                          args=(options.sensorId,
                                options.dest_host,
                                options.analyze))
        scanner.start()
    while True:
        print("start_main_loop: starting main loop")
        # Note -- config can change so need to re-read.
        config, port, delta = read_configuration(options.sensorId,
                                                 options.dest_host,
                                                 options.latitude,
                                                 options.longitude)
        tb = my_top_block(source, resamp, options, config, port, delta)
        try:
            main_loop(tb)
        except KeyboardInterrupt:
            sys.exit()
            os._exit(0)
            pass
        except:
            traceback.print_exc()


def sigusr2_handler(signo, frame):
    print("<<<<<<<<< got signal {!s}".format(signo))
    global tb
    tb.stop()
    sys.exit(0)
    os._exit(0)


def sigusr1_handler(signo, frame):
    time.sleep(1)
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    print("<<<<<<<<< got signal {!s}".format(signo))
    if "tb" in globals():
        global tb
        print("stopping task block")
        tb.disconnect_all()


if __name__ == '__main__':
    try:
        start_main_loop()
    except:
        traceback.print_exc()
        print("*******************************************************")
        print(" Ensure that mongodb is running on port 33000")
        print("*******************************************************")
