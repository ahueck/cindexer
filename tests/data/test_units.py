# RUN: %python %s

import unittest
import sys
import os
import time
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Load cindexer module
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)
import cindexer as cindex_pass

IndexManager = cindex_pass.IndexManager
TranslationUnitCache = cindex_pass.TranslationUnitCache
CompilationArgsResolver = cindex_pass.CompilationArgsResolver
DatabaseHandler = cindex_pass.DatabaseHandler
TypeFilter = cindex_pass.TypeFilter
TypeInfo = cindex_pass.TypeInfo


class TestUnits(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_db_and_resolver_integration(self):
        # Mocking raw DB output: compiler + flags
        # The DatabaseHandler.get_compile_args returns raw_args[1:]
        # which should then be passed to CompilationArgsResolver.resolve

        source = os.path.join(self.test_dir, "test.c")
        with open(source, "w") as f:
            f.write("int main() { return 0; }")

        # Mocking what DatabaseHandler would get from cmds[0].arguments
        raw_db_args = [
            "/usr/bin/gcc",
            "-DDEBUG",
            "-c",
            source,
            "-o",
            "test.o",
            "-I",
            "inc",
        ]

        # Simulating DatabaseHandler.get_compile_args(source) -> raw_db_args[1:]
        db_args = raw_db_args[1:]

        resolver = CompilationArgsResolver(self.test_dir)
        # extra_args might be empty
        full_args = db_args + []

        signature = resolver.resolve(full_args, source)

        # Expected: -DDEBUG, -I{abs_inc}
        expected = (
            "-DDEBUG",
            "-I",
            os.path.abspath(os.path.join(self.test_dir, "inc")),
        )
        self.assertEqual(signature, expected)

    def test_args_resolver_c_flag(self):
        # Cover 'if arg == "-c": continue'
        resolver = CompilationArgsResolver(self.test_dir)
        args = ["-c", "foo.c"]
        resolved = resolver.resolve(args, "foo.c")
        self.assertNotIn("-c", resolved)
        self.assertNotIn("foo.c", resolved)

    def test_cache_file_deleted(self):
        # Cover cache invalidation when file is deleted
        cache = TranslationUnitCache()
        source = os.path.join(self.test_dir, "temp_del.c")
        with open(source, "w") as f:
            f.write("int x;")

        sig = ("-DTEST",)

        # Put into cache
        cache.put(source, sig, [], {})

        # Verify it's there
        self.assertIsNotNone(cache.get(source, sig))

        # Delete file
        os.remove(source)

        # Verify get returns None (and triggers OSError handling)
        self.assertIsNone(cache.get(source, sig))

    def test_cache_dep_deleted(self):
        cache = TranslationUnitCache()
        source = os.path.join(self.test_dir, "temp_src.c")
        dep = os.path.join(self.test_dir, "temp_dep.h")

        with open(source, "w") as f:
            f.write("")
        with open(dep, "w") as f:
            f.write("")

        sig = ("-DTEST",)

        DependencyInfo = cindex_pass.DependencyInfo
        deps = {dep: DependencyInfo(dep, os.path.getmtime(dep), False)}

        cache.put(source, sig, [], deps)
        self.assertIsNotNone(cache.get(source, sig))

        os.remove(dep)
        # Should return None due to dep missing
        self.assertIsNone(cache.get(source, sig))

        os.remove(source)

    def test_cache_system_dep(self):
        # Cover 'if dep_info.is_system: continue'
        cache = TranslationUnitCache()
        source = os.path.join(self.test_dir, "temp_sys.c")
        with open(source, "w") as f:
            f.write("")

        sig = ("-DTEST",)
        dep_path = "/usr/include/stdio.h"  # Fake system path
        DependencyInfo = cindex_pass.DependencyInfo
        # Set mtime to something old
        deps = {dep_path: DependencyInfo(dep_path, 12345.0, True)}

        cache.put(source, sig, [], deps)

        entry = cache.get(source, sig)
        self.assertIsNotNone(entry)

        os.remove(source)

    def test_db_file_not_found(self):
        # Cover 'Warning: File ... not found in compilation database'
        # We need a mock DB
        with patch("clang.cindex.CompilationDatabase.fromDirectory") as mock_db_cls:
            mock_db = MagicMock()
            mock_db.getCompileCommands.return_value = None  # or empty list
            mock_db_cls.return_value = mock_db

            handler = DatabaseHandler(self.test_dir)
            args = handler.get_compile_args("non_existent.c")
            self.assertEqual(args, [])

    def test_db_init_error(self):
        # Cover DatabaseHandler init error
        err = cindex_pass.CompilationDatabaseError(0, "Mock Error")
        with patch("clang.cindex.CompilationDatabase.fromDirectory", side_effect=err):
            handler = DatabaseHandler("bad_dir")
            self.assertIsNone(handler.db)

    def test_type_filter_scope(self):
        # Cover 'if scope == "main": if info.filename != main_file: continue'
        infos = [
            TypeInfo(
                "A", "c:A", "Struct", "UserDefined", True, "main.c", 1, 1, "main.c"
            ),
            TypeInfo(
                "B", "c:B", "Struct", "UserDefined", True, "other.h", 1, 1, "main.c"
            ),
        ]

        filtered = TypeFilter.filter(infos, "main", "all", "main.c")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "A")

    def test_type_filter_decls(self):
        # Cover 'if decls == "defs": if not info.is_definition: continue'
        infos = [
            TypeInfo(
                "A", "c:A", "Struct", "UserDefined", True, "main.c", 1, 1, "main.c"
            ),
            TypeInfo(
                "B", "c:B", "Struct", "UserDefined", False, "main.c", 1, 1, "main.c"
            ),
        ]

        filtered = TypeFilter.filter(infos, "main", "defs", "main.c")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, "A")

        filtered_all = TypeFilter.filter(infos, "main", "all", "main.c")
        self.assertEqual(len(filtered_all), 2)

    def test_main_error_handling(self):
        # Verify IndexManager handles parse exceptions.
        manager = IndexManager(self.test_dir)
        # invalid source file that doesn't exist
        res, hit = manager.get_types("non_existent_file.c")
        self.assertEqual(res, [])
        self.assertFalse(hit)

    def test_basic_resolution(self):
        root = self.test_dir
        resolver = CompilationArgsResolver(root_dir=root)
        source = os.path.join(root, "src/main.c")

        args = ["-I", "include", "-DDEBUG", "-c", source, "-o", "main.o"]

        expected = ("-I", os.path.join(root, "include"), "-DDEBUG")

        result = resolver.resolve(args, source)
        self.assertEqual(result, expected)

    def test_joined_include(self):
        root = self.test_dir
        resolver = CompilationArgsResolver(root_dir=root)
        source = os.path.join(root, "main.c")
        args = ["-Iinclude", "-I/abs/path"]

        result = resolver.resolve(args, source)
        self.assertEqual(result, (f"-I{os.path.join(root, 'include')}", "-I/abs/path"))


class TestTranslationUnitCacheMethods(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cache = TranslationUnitCache()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_clear(self):
        source = os.path.join(self.test_dir, "test.c")
        with open(source, "w") as f:
            f.write("int x;")
        sig = ("-DTEST",)

        self.cache.put(source, sig, [], {})
        self.assertIsNotNone(self.cache.get(source, sig))

        self.cache.clear()
        self.assertIsNone(self.cache.get(source, sig))

    def test_remove(self):
        source = os.path.join(self.test_dir, "test.c")
        with open(source, "w") as f:
            f.write("int x;")
        sig = ("-DTEST",)

        self.cache.put(source, sig, [], {})
        self.assertIsNotNone(self.cache.get(source, sig))

        # Remove existing
        self.assertTrue(self.cache.remove(source, sig))
        self.assertIsNone(self.cache.get(source, sig))

        # Remove non-existent
        self.assertFalse(self.cache.remove(source, sig))


if __name__ == "__main__":
    unittest.main()
