// RUN: %dump_types --user-def --scope=all --format=text %s -- -I %S | %filecheck %s

#include "header.h"

// CHECK: Struct: HeaderStruct [Def]
// CHECK: Struct: MainStruct [Def]
struct MainStruct {
    int m;
};
