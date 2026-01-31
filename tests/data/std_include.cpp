// RUN: %dump_types --user-def --scope non-std --decls all --location --format=text %s | %filecheck %s --check-prefix=DEFAULT
// RUN: %dump_types --user-def --scope all --decls all --location --format=text %s | %filecheck %s --check-prefix=ALL

#include <vector>

struct __Hidden {
    int x;
};

struct _Hidden2 {
    int x;
};

struct Visible {
    int y;
};

int main() {
  std::vector<int> test;
  return test.capacity();
}

// DEFAULT-NOT: Struct: __Hidden
// DEFAULT-NOT: Struct: _Hidden2
// DEFAULT-NOT: TemplateClass: vector
// DEFAULT: Struct: Visible [Def] @ {{.*}}std_include.cpp

// ALL-NOT: Struct: __Hidden
// ALL-NOT: Struct: _Hidden2
// ALL: Struct: Visible [Def] @ {{.*}}std_include.cpp
// ALL: TemplateClass: vector
