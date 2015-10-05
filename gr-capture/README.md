# Build instructions

First make a build directory:

	mkdir build; cd build

To generate a makefile (from the build directory):

	cmake ../ -DCMAKE_INSTALL_PREFIX=$GNURADIO_HOME

Your I/Q capture block will appear in gnuradio companion.
