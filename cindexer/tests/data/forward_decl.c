// RUN: %dump_types --user-def --decls=all --format=text %s | %filecheck %s

struct MyForwardDecl;
struct MyDefinition {
    int a;
};

// CHECK: --- UserDefined ---
// CHECK:   Struct: MyDefinition [Def]
// CHECK:   Struct: MyForwardDecl [Decl]
