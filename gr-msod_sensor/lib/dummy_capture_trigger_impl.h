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

#ifndef INCLUDED_MSOD_SENSOR_DUMMY_CAPTURE_TRIGGER_IMPL_H
#define INCLUDED_MSOD_SENSOR_DUMMY_CAPTURE_TRIGGER_IMPL_H

#include <msod_sensor/dummy_capture_trigger.h>

namespace gr {
  namespace msod_sensor {

    class dummy_capture_trigger_impl : public dummy_capture_trigger
    {
     private:
	int d_itemcount;
	int d_itemsize;
	
     public:
      dummy_capture_trigger_impl(size_t itemsize);
      ~dummy_capture_trigger_impl();

      // Where all the action really happens
      int work(int noutput_items,
         gr_vector_const_void_star &input_items,
         gr_vector_void_star &output_items);
    };

  } // namespace msod_sensor
} // namespace gr

#endif /* INCLUDED_MSOD_SENSOR_DUMMY_CAPTURE_TRIGGER_IMPL_H */

