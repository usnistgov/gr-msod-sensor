rm CMakeCache.txt
cmake ../ -DCMAKE_EXE_LINKER_FLAGS="-lboost_log -lboost_log_setup -lpthread -lpthread" -DCMAKE_CXX_FLAGS="-DBOOST_LOG_DYN_LINK -std=c++11 -Wno-deprecated" -DMONGO_CLIENT_DIR=/raid/jnm11/mongo-cxx-driver/install -DOPENSSL_INSTALL_DIR=/home/mranga/openssl
