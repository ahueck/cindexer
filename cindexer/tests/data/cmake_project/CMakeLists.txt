cmake_minimum_required(VERSION 3.10)
project(TestDB)

add_definitions(-DREAL_PROJECT)

add_executable(test_bin src/test.cpp)
