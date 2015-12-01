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

#define IQCAPTURE_DEBUG

#include <gnuradio/io_signature.h>
#include <gnuradio/prefs.h>
#include "capture_sink_impl.h"
#include <ctime>
#include <fstream>
#include <iostream>
#ifdef IQCAPTURE_DEBUG
#include <gnuradio/logger.h>
#endif
#include <mongo/client/dbclient.h>
#include <exception>
#include <mongo/bson/bson.h>




namespace gr {
namespace msod_sensor {


capture_sink::sptr
capture_sink::make(size_t itemsize, size_t chunksize, char* capture_dir, int mongodb_port)
{
    return gnuradio::get_initial_sptr
           (new capture_sink_impl(itemsize, chunksize, capture_dir,mongodb_port));
}

/*
 * The private constructor
 */
capture_sink_impl::capture_sink_impl(size_t itemsize, size_t chunksize, char* capture_dir, int mongodb_port)
    : gr::sync_block("capture_sink",
                     gr::io_signature::make(1, 1, itemsize),
                     gr::io_signature::make(0, 0, 0))
{
    this->d_itemsize = itemsize;
    this->d_capture_dir = capture_dir;
    this->d_chunksize = chunksize;
    this->d_itemcount = 0;
    this->d_current_capture_file = NULL;
    this->generate_timestamp();
    std::string errmsg;
    try {
        if (!this->d_mongo_client.connect(std::string("127.0.0.1:") + std::to_string(mongodb_port) ,errmsg)) {
            GR_LOG_ERROR(d_debug_logger,"failed to initialize the client driver");
            throw std::runtime_error("cannot connect to Mongo Client");
        }
    } catch (std::exception& e) {
        GR_LOG_ERROR(d_debug_logger,"Unexpected exception");
        throw e;
    }
#ifdef IQCAPTURE_DEBUG
    prefs *p = prefs::singleton();
    std::string log_level = p->get_string("LOG", "log_level", "debug");
    GR_LOG_SET_LEVEL(d_debug_logger,log_level);
#endif
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
    if ( this->d_current_capture_file != NULL) {
	delete this->d_current_capture_file;
    }
    this->d_current_capture_file =  dirname;
}

void
capture_sink_impl::start_capture() {
    this->d_start_capture = true;
}

void
capture_sink_impl::stop_capture() {
    this->d_start_capture = false;
}


void
capture_sink_impl::set_data_message(char* data_message) {
    try {
        this->d_data_message = mongo::fromjson(std::string(data_message));
    } catch ( mongo::DBException& e) {
        GR_LOG_ERROR(d_debug_logger,"failed to initialize the client driver");
        throw std::runtime_error("Invalid data message");

    }
}



int
capture_sink_impl::work(int noutput_items,
                        gr_vector_const_void_star &input_items,
                        gr_vector_void_star &output_items)
{
    // Capture is not enabled.
    if (!this->d_start_capture) return noutput_items;
    // Capture is enabled.
    const char *in = (const char *) input_items[0];
    char *out = (char *) output_items[0];
    unsigned int byte_size = noutput_items * this->d_itemsize;
#ifdef IQCAPTURE_DEBUG
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::work byte_size " + std::to_string(byte_size));
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::work noutput_items " + std::to_string(noutput_items));
#endif
    int fd = open(this->d_current_capture_file->c_str(), O_APPEND | O_RDWR | O_CREAT, S_IWUSR | S_IRUSR);
    int buffercounter = 0;
    for (int i = 0 ; i < noutput_items; i++) {
        if ( this->d_itemcount >= this->d_chunksize) {
            close(fd);
            time_t  timev;
            time(&timev);
            mongo::BSONObjBuilder builder;
            builder.appendElements(this->d_data_message);
            mongo::BSONObj data_message = builder
                                          .append("_capture_file",*this->d_current_capture_file)
                                          .append("_capture_time",std::to_string(timev))
                                          .append("_sample_count",std::to_string(this->d_itemcount))
                                          .obj();
            // Insert the message into mongodb.
            try {
                this->d_mongo_client.insert("iqcapture.dataMessages",data_message);
            } catch (mongo::DBException& e) {
                GR_LOG_ERROR(d_debug_logger,"capture_sink_impl::Error inserting into mongodb ");
                return -1;
            }
#ifdef IQCAPTURE_DEBUG
            GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::data_message " + data_message.toString());
#endif
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

