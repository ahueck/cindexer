// RUN: %dump_types --user-def --format=text %s | %filecheck %s

// CHECK-DAG: Enum: Color [Def]
enum Color { RED, GREEN, BLUE };

// CHECK-DAG: Struct: Point [Def]
struct Point {
  int x;
  int y;
};

// CHECK-DAG: Typedef: Point2D [Def]
typedef struct Point Point2D;
