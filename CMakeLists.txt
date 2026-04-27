cmake_minimum_required(VERSION 3.15)

project(NanoTagHardware VERSION 0.1.0)
#set(VCPKG_VERBOSE true)

set(CMAKE_INSTALL_PREFIX "${PROJECT_BINARY_DIR}/")
set(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake" ${CMAKE_MODULE_PATH})

add_subdirectory(hardware)


