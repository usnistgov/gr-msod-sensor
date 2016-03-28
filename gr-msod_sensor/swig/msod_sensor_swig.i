/* -*- c++ -*- */

#define MSOD_SENSOR_API

%include "gnuradio.i"			// the common stuff

//load generated python docstrings
%include "msod_sensor_swig_doc.i"

%{
#include "msod_sensor/bin_aggregator_ff.h"
#include "msod_sensor/bin_statistics_ff.h"
#include "msod_sensor/file_descriptor_sink.h"
#include "msod_sensor/file_descriptor_source.h"
#include "msod_sensor/threshold_timestamp.h"
#include "msod_sensor/capture_sink.h"
#include "msod_sensor/iqcapture_sink.h"
#include "msod_sensor/dummy_capture_trigger.h"
#include "msod_sensor/level_capture_trigger.h"
%}

%include "msod_sensor/bin_aggregator_ff.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, bin_aggregator_ff);

%include "msod_sensor/bin_statistics_ff.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, bin_statistics_ff);
%include "msod_sensor/file_descriptor_sink.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, file_descriptor_sink);
%include "msod_sensor/file_descriptor_source.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, file_descriptor_source);
%include "msod_sensor/threshold_timestamp.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, threshold_timestamp);

%include "msod_sensor/capture_sink.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, capture_sink);

%include "msod_sensor/iqcapture_sink.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, iqcapture_sink);

%include "msod_sensor/dummy_capture_trigger.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, dummy_capture_trigger);
%include "msod_sensor/level_capture_trigger.h"
GR_SWIG_BLOCK_MAGIC2(msod_sensor, level_capture_trigger);
