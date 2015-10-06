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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include "capture_sink_impl.h"

namespace gr {
  namespace msod_sensor {

    capture_sink::sptr
    capture_sink::make(size_t itemsize, char* capture_dir, char* websocket_url)
    {
      return gnuradio::get_initial_sptr
        (new capture_sink_impl(itemsize, capture_dir, websocket_url));
    }

    /*
     * The private constructor
     */
    capture_sink_impl::capture_sink_impl(size_t itemsize, char* capture_dir, char* websocket_url)
      : gr::sync_block("capture_sink",
              gr::io_signature::make(1, 1, itemsize),
              gr::io_signature::make(0, 0, 0))
    {
	this->d_itemsize = itemsize;
	this->d_capture_dir = capture_dir;
	this->d_websocket_url = websocket_url;
    }

    /*
     * Our virtual destructor.
     */
    capture_sink_impl::~capture_sink_impl()
    {
    }

    int
    capture_sink_impl::work(int noutput_items,
        gr_vector_const_void_star &input_items,
        gr_vector_void_star &output_items)
    {
      const char *in = (const char *) input_items[0];
      char *out = (char *) output_items[0];
      unsigned long byte_size = noutput_items * d_itemsize;
      int fd = open("/tmp/capture", O_RDWR | O_APPEND | O_CREAT,S_IWUSR | S_IRUSR);
      while(byte_size > 0) {
            ssize_t r;
            r = write(fd, in, byte_size);
            if(r == -1) {
                  if(errno == EINTR)
                           continue;
                    else {
                           perror("file_descriptor_sink");
                           return -1;    // indicate we're done
                    }
             } else {
                      byte_size -= r;
                      in += r;
             }
      } 
      close(fd);

      return noutput_items;
    }

  } /* namespace capture */
} /* namespace gr */

