/* -*- c++ -*- */

#define CAPTURE_API

%include "gnuradio.i"			// the common stuff

//load generated python docstrings
%include "capture_swig_doc.i"

%{
#include "capture/iqcapture.h"
#include "capture/capture_sink.h"
%}


%include "capture/iqcapture.h"
GR_SWIG_BLOCK_MAGIC2(capture, iqcapture);
%include "capture/capture_sink.h"
GR_SWIG_BLOCK_MAGIC2(capture, capture_sink);
