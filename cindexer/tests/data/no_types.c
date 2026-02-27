// RUN: %dump_types --user-def --format=text %s | %filecheck %s

int main() {
    return 0;
}

// CHECK: --- UserDefined ---
// CHECK-NEXT: (None found)
// CHECK: --- Alias ---
// CHECK-NEXT: (None found)
