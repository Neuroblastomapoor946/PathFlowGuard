cmake_minimum_required(VERSION 3.18)
project(pathflow_qc_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(pathflow_qc_core
    src/qc_metrics.cpp
)

target_include_directories(pathflow_qc_core PUBLIC include)

add_executable(pathflow_qc_core_tests
    tests/qc_metrics_tests.cpp
)

target_link_libraries(pathflow_qc_core_tests PRIVATE pathflow_qc_core)

enable_testing()
add_test(NAME pathflow_qc_core_tests COMMAND pathflow_qc_core_tests)

