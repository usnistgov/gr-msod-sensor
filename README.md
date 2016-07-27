USRP sensor for MSOD with I/Q data capture capability

This is an extension and generalization of the USRP Spectrum Sensor.
It includes coarse grained streaming/posting capability and the ability to
log and analyze I/Q data when instructed to do so by an external agent
via MSOD.

Dependencies:
 
   gnuradio 3.6 +
   mongo-cxx-client 
 

To build this code:

1. Build dependencies:
   
   git clone mongo-cxx-driver  from github
   git checkout 26compat
   scons --full

2. Build the code

    mkdir build
    cd build 
    cmake ../ 
    make all 
    make install

See cmake/Modules for a list of dependencies and relevant environment variables.

To run the unit tests:

   Set the environment variable MSOD_WEB_HOST to where you have MSOD running.
   Define a sensor TestSensor
   Start mongod at port 33000
   cp testdata/testdata.bin /tmp
   cd build
   make test



Please contact mranga@nist.gov for information.


   
  


