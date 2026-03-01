// RUN: %dump_types --user-def --format=text --scope=non-sys -- -isystem %S/cmake_project/src %s | %filecheck %s

// The include is in a directory passed via -isystem, so it should be excluded
// even though it is not a standard header.
#include "test.cpp"

// CHECK: --- UserDefined ---
// CHECK: Struct: MainStruct [Def]
// CHECK-NOT: TestClass

struct MainStruct {
    int x;
};