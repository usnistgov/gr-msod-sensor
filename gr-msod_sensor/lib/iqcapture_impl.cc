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
#include "iqcapture_impl.h"
#include <sys/io.h>
#include <cstddef>
#include <stdio.h>

namespace gr {
  namespace msod_sensor {

    iqcapture::sptr
    iqcapture::make(size_t itemsize)
    {
      return gnuradio::get_initial_sptr
        (new iqcapture_impl(itemsize));
    }

    /*
     * The private constructor
     */
    iqcapture_impl::iqcapture_impl(size_t itemsize)
      : gr::block("iqcapture",
              gr::io_signature::make(1, 1, itemsize),
              gr::io_signature::make(1, 1, itemsize))
    {
	this->d_itemsize = itemsize;
    }

    /*
     * Our virtual destructor.
     */
    iqcapture_impl::~iqcapture_impl()
    {
    }

    void
    iqcapture_impl::forecast (int noutput_items, gr_vector_int &ninput_items_required)
    {
         ninput_items_required[0] = noutput_items;
    }

    int
    iqcapture_impl::general_work (int noutput_items,
                       gr_vector_int &ninput_items,
                       gr_vector_const_void_star &input_items,
                       gr_vector_void_star &output_items)
    {
 	char  *in = (char*)input_items[0];
        char *out = (char *) output_items[0];
        unsigned long byte_size = noutput_items * d_itemsize;
        // Do <+signal processing+>
        // Tell runtime system how many input items we consumed on
        // each input stream.
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
      // Pass through.
      // reset the ptr and counter to beginning of the buffer.
      in = (char*)input_items[0];
      byte_size = noutput_items * d_itemsize;
      memcpy(out,in,byte_size);
      consume_each (noutput_items);
      return noutput_items;
    }

  } /* namespace capture */
} /* namespace gr */

