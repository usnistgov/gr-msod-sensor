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

#ifndef INCLUDED_CAPTURE_CAPTURE_SINK_IMPL_H
#define INCLUDED_CAPTURE_CAPTURE_SINK_IMPL_H

#include <msod_sensor/capture_sink.h>
#include <fstream>

namespace gr {
  namespace msod_sensor {

    class capture_sink_impl : public capture_sink
    {
     private:
      // Nothing to declare in this block.
      char*  d_capture_dir;
      int    d_itemsize;
      char*  d_websocket_url; 
      size_t d_chunksize;
      long   d_itemcount;
      std::ofstream d_logfile;
      std::string* d_current_capture_file;

      void generate_timestamp();

     public:
      capture_sink_impl(size_t itemsize, size_t chunksize, char* capture_dir);
      ~capture_sink_impl();
      // Where all the action really happens
      int work(int noutput_items,
         gr_vector_const_void_star &input_items,
         gr_vector_void_star &output_items);
    };
      

  } // namespace capture
} // namespace gr

#endif /* INCLUDED_CAPTURE_CAPTURE_SINK_IMPL_H */

