/* -*- c++ -*- */
/* 
 * Copyright 2015 <+YOU OR YOUR COMPANY+>.
 * 
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 * 
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifndef INCLUDED_MSOD_SENSOR_IQCAPTURE_SINK_IMPL_H
#define INCLUDED_MSOD_SENSOR_IQCAPTURE_SINK_IMPL_H

#include <msod_sensor/iqcapture_sink.h>

#include <mongo/client/dbclient.h>
#include <mongo/bson/bson.h>
#include <msod_sensor/capture_sink.h>
#include <pmt/pmt.h>
#include <fstream>
#include <list>
namespace gr {
  namespace msod_sensor {

    class iqcapture_sink_impl : public iqcapture_sink
    {
     private:
      char*  d_capture_dir;
      int    d_itemsize;
      char*  d_websocket_url; 
      size_t d_chunksize;
      long   d_itemcount;
      bool   d_start_capture;
      int    d_buffer_counter;
      mongo::BSONObj d_data_message;
      std::ofstream d_logfile;
      std::string* d_current_capture_file;
      mongo::DBClientConnection d_mongo_client;
      // I/Q samples are stored in this queue and written out 
      // on a start-capture command
      std::list<char*> d_capture_queue;

      void generate_timestamp();
      // start capture and write out whatever is in the buffer.
      // This is triggered by an external trigger (for example something that detects
      // LTE downlink).
      void capture(pmt::pmt_t msg);
     public:
      iqcapture_sink_impl(size_t itemsize, size_t chunksize, char* capture_dir,int mongodb_port);
      ~iqcapture_sink_impl();
      // set the sensor id (for posting to the database).
      void set_data_message(char* data_message);
      // Where all the action really happens
      int work(int noutput_items,
         gr_vector_const_void_star &input_items,
         gr_vector_void_star &output_items);
    };

  } // namespace msod_sensor
} // namespace gr

#endif /* INCLUDED_MSOD_SENSOR_IQCAPTURE_SINK_IMPL_H */

