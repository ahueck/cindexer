# RUN: rm -rf %t
# RUN: mkdir -p %t/proj/build
# RUN: cp -r %S/cmake_project/src %t/proj/src
# RUN: cp %S/cmake_project/CMakeLists.txt %t/proj/CMakeLists.txt

# Generate compile_commands.json in %t/proj/build
# RUN: %cmake -S %t/proj -B %t/proj/build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > /dev/null

# Test 1: Auto-detection (compile_commands.json in ../build)
# RUN: %dump_types --user-def --format=text %t/proj/src/test.cpp | %filecheck %S/cmake_project/src/test.cpp

# Debug: check DB content
# RUN: cat %t/proj/build/compile_commands.json

# Test 2: Invalid build directory
# RUN: %dump_types --user-def --format=text -p %t/nonexistent/path %t/proj/src/test.cpp 2>&1 | %filecheck %s --check-prefix=BAD-DB

# BAD-DB: Warning: Could not load compilation database from {{.*}}nonexistent/path

# Test 4: Truly no database found anywhere
# RUN: touch %t/no_db.c
# RUN: %dump_types --user-def --format=text %t/no_db.c | %filecheck %s --check-prefix=NO-DB

# NO-DB: --- UserDefined ---
# NO-DB-NEXT: (None found)

# Test 5: Invalid file (should fail to load)
# RUN: ! %dump_types --user-def /nonexistent/file.c 2>&1 | %filecheck %s --check-prefix=NO-TU
# NO-TU: Error: Unable to load input.
