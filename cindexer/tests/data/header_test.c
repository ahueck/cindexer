// RUN: %dump_types --user-def --scope=all --format=text %s -- -I %S | %filecheck %s --check-prefix=scoped
// RUN: %dump_types --user-def --scope=main --format=text %s -- -I %S | %filecheck %s --check-prefix=filtered

#include "header.h"

// scoped: Struct: HeaderStruct [Def]
// scoped: Struct: MainStruct [Def]
// filtered-NOT: HeaderStruct [Def]
struct MainStruct {
    int m;
};
