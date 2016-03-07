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
    HINTS ${PC_MONGO_CLIENT_DIR}
    PATHS
    ${MONGO_CLIENT_DIR}/lib
    /usr/local/lib
    /usr/lib
)

LIST(APPEND MONGO_CLIENT_LIBRARY ${CMAKE_DL_LIBS})

INCLUDE(FindPackageHandleStandardArgs)
