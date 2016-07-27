rm CMakeCache.txt
cmake ../ -DCMAKE_EXE_LINKER_FLAGS="-lboost_log -lboost_log_setup -lpthread -lpthread" -DCMAKE_CXX_FLAGS="-DBOOST_LOG_DYN_LINK -std=c++11 -Wno-deprecated -fPIC" -DMONGO_CLIENT_DIR=$MONGO_CLIENT_DIR  -DCMAKE_INSTALL_PREFIX=$GNURADIO_HOME

#-DOPENSSL_INSTALL_DIR=/home/mranga/openssl
