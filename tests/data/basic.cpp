namespace Math {
// CHECK: Class: Vector3 [Def]
class Vector3 {
public:
  float x, y, z;
};
} // namespace Math

// CHECK: Class: Box [Def]
template <typename T> class Box {
  T value;
};

// CHECK: Using: FloatBox [Def]
using FloatBox = Box<float>;

