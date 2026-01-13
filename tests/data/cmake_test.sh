; RUN: mkdir -p %t/build
; RUN: cmake -S %S/cmake_project -B %t/build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > /dev/null

; RUN: %dump_types --user-def --format=text -p %t/build %S/cmake_project/src/test.cpp | %filecheck %S/cmake_project/src/test.cpp