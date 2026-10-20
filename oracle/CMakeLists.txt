cmake_minimum_required(VERSION 3.16)
project(crypto_mixed_oracle LANGUAGES CXX)

# Out-of-tree minimized Botan 3.13.0 build produced by oracle/build_upstream.sh.
set(BOTAN_BUILD_DIR "" CACHE PATH "Botan configure.py build directory")
if(NOT BOTAN_BUILD_DIR)
  message(FATAL_ERROR "set -DBOTAN_BUILD_DIR to the Botan build directory")
endif()

add_executable(oracle_driver driver.cpp)
target_compile_features(oracle_driver PRIVATE cxx_std_20)
target_include_directories(oracle_driver PRIVATE ${BOTAN_BUILD_DIR}/build/include/public)
target_link_libraries(oracle_driver PRIVATE ${BOTAN_BUILD_DIR}/libbotan-3.a)
