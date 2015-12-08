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
#include <gnuradio/logger.h>
#include <mongo/bson/bson.h>
#include <mongo/client/dbclient.h>
#include <ctime>
#include <fstream>
#include <iostream>
#include <exception>
#undef NDEBUG
#include <cassert>
#include "capture_sink_impl.h"




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
    :gr::sync_block("capture_sink",
                     gr::io_signature::make(1, 1, itemsize),
                     gr::io_signature::make(0, 0, 0))
{
    prefs *p = prefs::singleton();
#ifdef IQCAPTURE_DEBUG
    std::string log_level = p->get_string("LOG", "log_level", "debug");
#else
    std::string log_level = p->get_string("LOG", "log_level", "info");
#endif
    GR_LOG_SET_LEVEL(d_debug_logger,log_level);
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl:: itemsize = " + std::to_string(itemsize) + " chunksize = " + std::to_string(chunksize) + 
	" capture_dir = "  + capture_dir  );

    d_itemsize = itemsize;
    d_capture_dir = new char[strlen(capture_dir) + 1];
    strcpy(d_capture_dir,capture_dir);
    d_chunksize = chunksize;
    d_itemcount = 0;
    d_current_capture_file = NULL;
    d_capture_buffer = new char*[chunksize];
    memset(d_capture_buffer,0,sizeof(d_capture_buffer));
    generate_timestamp();
    d_start_capture = false;
    std::string errmsg;
    try {
        if (!d_mongo_client.connect(std::string("127.0.0.1:") + std::to_string(mongodb_port) ,errmsg)) {
            GR_LOG_ERROR(d_debug_logger,"failed to initialize the client driver");
            throw std::runtime_error("cannot connect to Mongo Client");
        }
    	GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl:: connected to mongod ");
    } catch (std::exception& e) {
        GR_LOG_ERROR(d_debug_logger,"Unexpected exception");
        throw e;
    }

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
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::generate_timestamp ");
    time_t  timev;
    time(&timev);
    std::string* dirname = new std::string(d_capture_dir);
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
    if ( d_current_capture_file != NULL) {
	delete d_current_capture_file;
    }
    d_current_capture_file =  dirname;
}

void
capture_sink_impl::start_capture() {
#ifdef IQCAPTURE_DEBUG
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::start_capture ");
#endif
    d_start_capture = true;
}

void
capture_sink_impl::stop_capture() {
#ifdef IQCAPTURE_DEBUG
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::stop_capture ");
#endif
    d_start_capture = false;
}


void
capture_sink_impl::set_data_message(char* data_message) {
    try {
        d_data_message = mongo::fromjson(std::string(data_message));
    } catch ( mongo::DBException& e) {
        GR_LOG_ERROR(d_debug_logger,"failed to initialize the client driver");
        throw std::runtime_error("Invalid data message");
    }
}


/**
* Dump the existing buffer into a file and push a record into mongodb.
*/

bool
capture_sink_impl::dump_buffer() {
    int buffercounter = 0;
    d_start_capture = false;
    generate_timestamp();
    GR_LOG_ERROR(d_debug_logger,"capture_sink_impl::dump_buffer: logging to  : " + *d_current_capture_file );
    assert(d_itemcount == d_chunksize);
    int fd = open(d_current_capture_file->c_str(), O_RDWR | O_CREAT, S_IWUSR | S_IRUSR);
    if (fd < 0 ) {
    	GR_LOG_ERROR(d_debug_logger,"capture_sink_impl::dump_buffer: open failed on : " + *d_current_capture_file->c_str());
	return false;
    }
    int count = 0;
    for (int i = 0; i < d_itemcount; i++) {
	char* item = d_capture_buffer[i];
        GR_LOG_ERROR(d_debug_logger,"capture_sink_impl::dump_buffer: logging to  : " + std::to_string(i) + "\n");
	assert(item != NULL);
        int written = write(fd,item,d_itemsize);
	if (written != d_itemsize) {
    		GR_LOG_ERROR(d_debug_logger,"capture_sink_impl::dump_buffer: write failed. written =  " + std::to_string(written) 
				+ " d_itemsize " + std::to_string(d_itemsize) + " item " );
		return false;
	}
	count ++;
    }
    close(fd);
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::dump_buffer: wrote " + std::to_string(count) + " elements to file : " + *d_current_capture_file);
    time_t  timev;
    time(&timev);
    mongo::BSONObjBuilder builder;
    builder.appendElements(d_data_message);
    mongo::BSONObj data_message = builder.append("_capture_file",*d_current_capture_file)
                                          .append("_capture_time",std::to_string(timev))
                                          .append("_sample_count",std::to_string(d_itemcount))
                                          .obj();
    // Insert the message into mongodb.
    try {
        d_mongo_client.insert("iqcapture.dataMessages",data_message);
    } catch (mongo::DBException& e) {
        GR_LOG_ERROR(d_debug_logger,"capture_sink_impl::Error inserting into mongodb ");
        return false;
    }
#ifdef IQCAPTURE_DEBUG
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::data_message " + data_message.toString());
#endif
    clear_buffer();
    return true;
}


void
capture_sink_impl::clear_buffer() {
    // Clear the capture vector. This also deletes the elements of the capture buffer.
    for (int i = 0; i < d_itemcount; i++) {
	delete d_capture_buffer[i];
    }
    d_itemcount = 0;
}



int
capture_sink_impl::work(int noutput_items,
                        gr_vector_const_void_star &input_items,
                        gr_vector_void_star &output_items)
{

    // Capture is enabled.
    const char *in = (const char *) input_items[0];
    char *out = (char *) output_items[0];
    // Capture is not enabled. Just pass through.
    if (!d_start_capture) return noutput_items;
    unsigned int byte_size = noutput_items * d_itemsize;
#ifdef IQCAPTURE_DEBUG
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::work byte_size " + std::to_string(byte_size));
    GR_LOG_DEBUG(d_debug_logger,"capture_sink_impl::work noutput_items " + std::to_string(noutput_items));
#endif
    int buffercounter = 0;
    for (int i = 0; i < noutput_items; i++ ) {
	char* item =  (char*) (in + buffercounter);
	buffercounter = buffercounter + d_itemsize;
	// Exceeded our storage capacity? So dump the buffer and clear it.
	if (d_itemcount ==  d_chunksize) {
	    if (d_start_capture) {
		if (! dump_buffer() ) return -1;
	    } else {
		clear_buffer();
	    }
	} 
	// Our queue is not yet full.
	char* newitem  = new char[d_itemsize];
	assert(newitem != NULL);
	memcpy(newitem,item,d_itemsize);
	d_capture_buffer[d_itemcount] = newitem;
	d_itemcount++;
    }
    return noutput_items;
}

} /* namespace capture */
} /* namespace gr */

