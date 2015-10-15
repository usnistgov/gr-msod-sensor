rm CMakeCache.txt
cmake ../ -DCMAKE_EXE_LINKER_FLAGS="-lboost_log -lboost_log_setup -lpthread -std=c++11" -DCMAKE_SHARED_LINKER_FLAGS="-lboost_log_setup -lboost_log -lpthread" -DCMAKE_MODULE_LINKER_FLAGS="-lboost_log_setup -lboost_log -lpthread" -DCMAKE_CXX_FLAGS="-DBOOST_LOG_DYN_LINK -std=c++11"
