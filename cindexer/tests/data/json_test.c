// RUN: %dump_types --user-def --format=json %s | %filecheck %s
// RUN: %dump_types --user-def --format=json --location %s | %filecheck %s --check-prefix=LOC

struct JsonStruct {
    int j;
};

// CHECK: [
// CHECK:   {
// CHECK:     "name": "JsonStruct",
// CHECK:     "kind": "Struct",
// CHECK:     "category": "UserDefined",
// CHECK:     "is_definition": true
// CHECK-NOT: "location":
// CHECK:   }
// CHECK: ]

// LOC: "location": {
// LOC:   "file": "{{.*}}json_test.c",
// LOC:   "line": 4,
// LOC:   "column": 8
// LOC: }
