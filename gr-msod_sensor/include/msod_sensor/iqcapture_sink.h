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


#ifndef INCLUDED_MSOD_SENSOR_IQCAPTURE_SINK_H
#define INCLUDED_MSOD_SENSOR_IQCAPTURE_SINK_H

#include <msod_sensor/api.h>
#include <gnuradio/sync_block.h>

namespace gr {
  namespace msod_sensor {

    /*!
     * \brief <+description of block+>
     * \ingroup msod_sensor
     *
     */
    class MSOD_SENSOR_API iqcapture_sink : virtual public gr::sync_block
    {
     public:
      typedef boost::shared_ptr<iqcapture_sink> sptr;

      /*!
       * \brief Return a shared_ptr to a new instance of msod_sensor::iqcapture_sink.
       *
       * To avoid accidental use of raw pointers, msod_sensor::iqcapture_sink's
       * constructor is in a private implementation
       * class. msod_sensor::iqcapture_sink::make is the public interface for
       * creating new instances.
       */
      static sptr make(size_t itemsize, size_t chunksize, char* capture_dir);
    };

  } // namespace msod_sensor
} // namespace gr

#endif /* INCLUDED_MSOD_SENSOR_IQCAPTURE_SINK_H */

