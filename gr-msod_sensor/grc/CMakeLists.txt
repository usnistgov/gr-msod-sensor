# Copyright 2011 Free Software Foundation, Inc.
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
install(FILES
    msod_sensor_bin_aggregator_ff.xml
    msod_sensor_bin_statistics_ff.xml
    msod_sensor_file_descriptor_sink.xml
    msod_sensor_file_descriptor_source.xml
    msod_sensor_websocket_sink.xml
    msod_sensor_sslsocket_sink.xml
    msod_sensor_threshold_timestamp.xml
    msod_sensor_capture_sink.xml
    msod_sensor_iqcapture_sink.xml
    msod_sensor_dummy_capture_trigger.xml
    msod_sensor_level_capture_trigger.xml DESTINATION share/gnuradio/grc/blocks
)
