/* -*- c++ -*- */
/* 
 * Copyright 2016 <+YOU OR YOUR COMPANY+>.
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


#ifndef INCLUDED_MSOD_SENSOR_LEVEL_CAPTURE_TRIGGER_H
#define INCLUDED_MSOD_SENSOR_LEVEL_CAPTURE_TRIGGER_H

#include <msod_sensor/api.h>
#include <gnuradio/block.h>

namespace gr {
  namespace msod_sensor {

    /*!
     * \brief <+description of block+>
     * \ingroup msod_sensor
     *
     */
    class MSOD_SENSOR_API level_capture_trigger : virtual public gr::block
    {
     public:
      typedef boost::shared_ptr<level_capture_trigger> sptr;

      /*!
       * \brief Return a shared_ptr to a new instance of msod_sensor::level_capture_trigger.
       *
       * To avoid accidental use of raw pointers, msod_sensor::level_capture_trigger's
       * constructor is in a private implementation
       * class. msod_sensor::level_capture_trigger::make is the public interface for
       * creating new instances.
       */
      static sptr make(size_t itemsize, int level, size_t window_size);

      /*!
       * \brief Start capture
       */
      virtual void arm() = 0;

      /*!
       * \brief Stop capture.
       */
      virtual void disarm() = 0;
    };

  } // namespace msod_sensor
} // namespace gr

#endif /* INCLUDED_MSOD_SENSOR_LEVEL_CAPTURE_TRIGGER_H */

