// clang-format off
// RUN: %dump_types --user-def --format=text %s | %filecheck %s
// RUN: %dump_types --user-def --format=text %s -- -DUNDEFINED_TEST | %filecheck \
// RUN: %s --check-prefix DEF

#ifdef UNDEFINED_TEST
// CHECK-NOT: Enum: Color [Def]
// DEF: Enum: Color [Def]
enum Color { RED, GREEN, BLUE };
#endif

// CHECK: Struct: Point [Def]
// DEF: Struct: Point [Def]
struct Point {
  int x;
  int y;
};
