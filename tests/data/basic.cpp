// RUN: %dump_types --user-def --format=text %s | %filecheck %s

namespace Math {
// CHECK-DAG: Class: Vector3 [Def]
class Vector3 {
public:
  float x, y, z;
};
} // namespace Math

// CHECK-DAG: Class: Box [Def]
template <typename T> class Box {
  T value;
};

// CHECK-DAG: Using: FloatBox [Def]
using FloatBox = Box<float>;
