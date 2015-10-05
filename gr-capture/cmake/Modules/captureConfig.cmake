INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_CAPTURE capture)

FIND_PATH(
    CAPTURE_INCLUDE_DIRS
    NAMES capture/api.h
    HINTS $ENV{CAPTURE_DIR}/include
        ${PC_CAPTURE_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    CAPTURE_LIBRARIES
    NAMES gnuradio-capture
    HINTS $ENV{CAPTURE_DIR}/lib
        ${PC_CAPTURE_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
)

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(CAPTURE DEFAULT_MSG CAPTURE_LIBRARIES CAPTURE_INCLUDE_DIRS)
MARK_AS_ADVANCED(CAPTURE_LIBRARIES CAPTURE_INCLUDE_DIRS)

