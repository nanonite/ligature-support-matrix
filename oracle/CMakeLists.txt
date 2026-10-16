cmake_minimum_required(VERSION 3.16)
project(date_creusot_oracle LANGUAGES CXX)

add_executable(oracle_driver driver.cpp)
target_compile_features(oracle_driver PRIVATE cxx_std_17)
target_include_directories(oracle_driver PRIVATE ${CMAKE_SOURCE_DIR}/../upstream/date/include)
