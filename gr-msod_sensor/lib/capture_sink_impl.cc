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

//#define IQCAPTURE_DEBUG


#include <gnuradio/io_signature.h>
#include "capture_sink_impl.h"
#include <ctime>
#include <fstream>
#include <iostream>
#ifdef IQCAPTURE_DEBUG
#include <boost/log/trivial.hpp>
namespace logging = boost::log;
namespace src = boost::log::sources;
namespace sinks = boost::log::sinks;
#endif




namespace gr {
  namespace msod_sensor {


    capture_sink::sptr
    capture_sink::make(size_t itemsize, size_t chunksize, char* capture_dir)
    {
      return gnuradio::get_initial_sptr
        (new capture_sink_impl(itemsize, chunksize, capture_dir));
    }

    /*
     * The private constructor
     */
    capture_sink_impl::capture_sink_impl(size_t itemsize, size_t chunksize, char* capture_dir)
      : gr::sync_block("capture_sink",
              gr::io_signature::make(1, 1, itemsize),
              gr::io_signature::make(0, 0, 0))
    {
	this->d_itemsize = itemsize;
	this->d_capture_dir = capture_dir;
	this->d_chunksize = chunksize;
	this->d_itemcount = 0;
	this->generate_timestamp();
    }

    /*
     * Our virtual destructor.
     */
    capture_sink_impl::~capture_sink_impl()
    {
    }

    /*
    * Generate a file name (timestamped).
    */
    void capture_sink_impl::generate_timestamp() {
	time_t  timev;
	time(&timev);
      	std::string* dirname = new std::string(this->d_capture_dir);
      	dirname->append("/capture-");
	std::string time_stamp = std::to_string(timev);
      	dirname->append(time_stamp);
	struct stat statbuf;
	if ( stat(dirname->c_str(),&statbuf) != -1 ) {
		for (int counter = 1 ; counter < 1000; counter++) {
			std::string* temp_dirname = new  std::string(*dirname);
	   		temp_dirname->append(".");
	   		temp_dirname->append(std::to_string(counter));
			if ( stat(temp_dirname->c_str(),&statbuf) == -1 ) {
			   delete dirname;
			   dirname = temp_dirname;
			   break;
			} else {
			   delete temp_dirname;
			}
		}
	}
	this->d_current_capture_file =  dirname;
    }

    int
    capture_sink_impl::work(int noutput_items,
        gr_vector_const_void_star &input_items,
        gr_vector_void_star &output_items)
    {
      const char *in = (const char *) input_items[0];
      char *out = (char *) output_items[0];
      unsigned int byte_size = noutput_items * this->d_itemsize;
      #ifdef IQCAPTURE_DEBUG 
      this->logger << "capture_sink_impl::work: byte_size " << byte_size << "\n";
      this->logger << "capture_sink_impl::work: noutput_items " << noutput_items << "\n";
      #endif
      int fd = open(this->d_current_capture_file->c_str(), O_APPEND | O_RDWR | O_CREAT, S_IWUSR | S_IRUSR);
      int buffercounter = 0;
      for (int i = 0 ; i < noutput_items; i++) {
	 if ( this->d_itemcount >= this->d_chunksize) {
	    close(fd);
	    generate_timestamp();
      	    fd = open(this->d_current_capture_file->c_str(), O_APPEND | O_RDWR | O_CREAT, S_IWUSR | S_IRUSR);
	    this->d_itemcount = 0;
	 }
	 int written = write(fd,in + buffercounter,d_itemsize);
	 if ( written != d_itemsize ) {
           perror("capture_sink");
           return -1;    // indicate we're done
	 }
	 this->d_itemcount ++;
	 buffercounter += d_itemsize;
      }
      close(fd);
      return noutput_items;
    }

  } /* namespace capture */
} /* namespace gr */

