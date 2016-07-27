# http://www.cmake.org/pipermail/cmake/2006-October/011446.html
# Modified to use pkg config and use standard var names

#
# Find the CppUnit includes and library
#
# This module defines
# CPPUNIT_INCLUDE_DIR, where to find tiff.h, etc.
# CPPUNIT_LIBRARIES, the libraries to link against to use CppUnit.
# CPPUNIT_FOUND, If false, do not try to use CppUnit.

INCLUDE(FindPkgConfig)


FIND_LIBRARY(MONGO_CLIENT_LIBRARY
    NAMES libmongoclient.a
    HINTS $ENV{MONGO_CLIENT_DIR}/lib
    HINTS ${PC_MONGO_CLIENT_DIR}
    PATHS
    ${MONGO_CLIENT_DIR}/lib
    /usr/local/lib
    /usr/lib
)
mark_as_advanced(MONGO_CLIENT_LIBRARY)

find_path(MONGO_INCLUDE_DIR 
    HINTS $ENV{MONGO_CLIENT_DIR}/include
    NAMES mongo/client/dbclient.h
    PATHS
    ${MONGO_CLIENT_DIR}/include
    /usr/local/include
    /usr/include
)

mark_as_advanced(MONGO_INCLUDE_DIR)

message(STATUS "MONGO_CLIENT_LIBRARY " ${MONGO_CLIENT_LIBRARY})
message(STATUS "MONGO_INCLUDE_DIR " ${MONGO_INCLUDE_DIR})

INCLUDE(FindPackageHandleStandardArgs)
