// RUN: %dump_types --user-def --scope all --decls all --location --format=text %s | %filecheck %s --check-prefix=DEFAULT
// RUN: %dump_types --user-def --scope all --decls all --location --format=text --show-std %s | %filecheck %s --check-prefix=SHOW-STD

#include <vector>

struct __Hidden {
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
// DEFAULT-NOT: TemplateClass: vector
// DEFAULT: Struct: Visible [Def] @ {{.*}}std_include.cpp

// SHOW-STD-NOT: Struct: __Hidden
// SHOW-STD: Struct: Visible [Def] @ {{.*}}std_include.cpp
// SHOW-STD: TemplateClass: vector