cmake_minimum_required(VERSION 3.16)
project(swisstable_oracle LANGUAGES CXX)

set(ABSL_BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(ABSL_PROPAGATE_CXX_STD ON CACHE BOOL "" FORCE)
add_subdirectory(
  "${CMAKE_CURRENT_SOURCE_DIR}/../upstream/abseil-cpp"
  "${CMAKE_CURRENT_BINARY_DIR}/abseil-cpp"
  EXCLUDE_FROM_ALL)

add_executable(oracle_driver driver.cpp)
target_compile_features(oracle_driver PRIVATE cxx_std_17)
target_link_libraries(oracle_driver PRIVATE absl::flat_hash_map)
