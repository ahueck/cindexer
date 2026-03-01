#ifdef REAL_PROJECT
// CHECK: Struct: DbSuccess [Def]
struct DbSuccess {};
#else
// CHECK-NOT: Struct: DbFailure [Def]
struct DbFailure {};
#endif