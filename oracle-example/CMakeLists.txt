cmake_minimum_required(VERSION 3.16)
project(oracle_example LANGUAGES CXX)

add_executable(oracle_driver driver.cpp)
target_compile_features(oracle_driver PRIVATE cxx_std_17)
