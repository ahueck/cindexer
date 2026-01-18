# RUN: %python %s

import unittest
import sys
import os
import time
import unittest.mock

# Load cindexer module
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)
from cindexer import IndexManager


class TestIndexManager(unittest.TestCase):
    def setUp(self):
        # Create a temp source file
        self.test_dir = os.path.join(project_root, "tests", "data", "manager_test_tmp")
        os.makedirs(self.test_dir, exist_ok=True)
        self.source_file = os.path.join(self.test_dir, "test.c")
        self.header_file = os.path.join(self.test_dir, "header.h")

        with open(self.header_file, "w") as f:
            f.write("struct HeaderStruct { int x; };\n")

        with open(self.source_file, "w") as f:
            f.write('#include "header.h"\n')
            f.write("struct MainStruct { int y; };\n")

    def tearDown(self):
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_caching(self):
        manager = IndexManager(project_root=self.test_dir)

        # First pass - should parse (Miss)
        opts = {"scope": "all", "decls": "all"}
        args = ["-I", self.test_dir]

        types1, hit1 = manager.get_types(self.source_file, args, opts)
        self.assertEqual(len(types1), 2)  # HeaderStruct, MainStruct
        self.assertFalse(hit1)

        # Access cache directly to verify entry exists
        # We need to resolve the signature manually to check the key
        signature = manager._resolve_signature(self.source_file, args)
        cached_entry = manager.cache.get(self.source_file, signature)
        self.assertIsNotNone(cached_entry)

        # Second pass - should hit cache
        types2, hit2 = manager.get_types(self.source_file, args, opts)
        self.assertEqual(len(types2), 2)
        self.assertTrue(hit2)

        # Modify header
        time.sleep(1.1)  # Ensure mtime changes
        os.utime(self.header_file, None)

        # Should invalidate cache
        cached_entry_after_touch = manager.cache.get(self.source_file, signature)
        self.assertIsNone(cached_entry_after_touch)

        # Reparse (Miss)
        types3, hit3 = manager.get_types(self.source_file, args, opts)
        self.assertEqual(len(types3), 2)
        self.assertFalse(hit3)

        # Verify it's back in cache
        cached_entry_new = manager.cache.get(self.source_file, signature)
        self.assertIsNotNone(cached_entry_new)
        self.assertNotEqual(cached_entry, cached_entry_new)

    def test_ignore_cache(self):
        manager = IndexManager(project_root=self.test_dir)
        args = ["-I", self.test_dir]

        # First pass - miss
        _, hit1 = manager.get_types(self.source_file, args)
        self.assertFalse(hit1)

        # Second pass - hit
        _, hit2 = manager.get_types(self.source_file, args)
        self.assertTrue(hit2)

        # Third pass with ignore_cache - should report miss
        _, hit3 = manager.get_types(self.source_file, args, ignore_cache=True)
        self.assertFalse(hit3)

    def test_clear_cache(self):
        manager = IndexManager(project_root=self.test_dir)
        args = ["-I", self.test_dir]

        manager.get_types(self.source_file, args)

        # Verify cached
        _, hit = manager.get_types(self.source_file, args)
        self.assertTrue(hit)

        # Clear
        manager.clear_cache()

        # Should be miss now
        _, hit_after = manager.get_types(self.source_file, args)
        self.assertFalse(hit_after)

    def test_clear_cache_for_tu(self):
        manager = IndexManager(project_root=self.test_dir)
        args = ["-I", self.test_dir]

        manager.get_types(self.source_file, args)

        # Verify cached
        _, hit = manager.get_types(self.source_file, args)
        self.assertTrue(hit)

        # Clear specific TU
        removed = manager.clear_cache_for_tu(self.source_file, args)
        self.assertTrue(removed)

        # Should be miss now
        _, hit_after = manager.get_types(self.source_file, args)
        self.assertFalse(hit_after)

    def test_fuzzy_resolution_merge(self):
        src1 = os.path.join(self.test_dir, "part_A.c")
        src2 = os.path.join(self.test_dir, "part_B.c")

        with open(src1, "w") as f:
            f.write("struct A { int a; };")
        with open(src2, "w") as f:
            f.write("struct B { int b; };")

        manager = IndexManager(project_root=self.test_dir)

        def mock_find(partial):
            if partial == "part":
                return [src1, src2]
            # Fallback for explicit paths
            if os.path.exists(partial):
                return [os.path.abspath(partial)]
            return [partial]

        with unittest.mock.patch.object(
            manager.db_handler, "find_matching_files", side_effect=mock_find
        ):
            # 1. Query "part" -> matches both
            types, hit = manager.get_types("part")
            names = sorted([t.name for t in types])
            self.assertEqual(names, ["A", "B"])
            self.assertFalse(hit)

            # 2. Query again -> should hit cache
            types2, hit2 = manager.get_types("part")
            self.assertTrue(hit2)
            self.assertEqual(len(types2), 2)

            # 3. Clear cache for ONE file
            # We pass absolute path src1. mock_find returns [src1].
            manager.clear_cache_for_tu(src1)

            # 4. Query "part" again -> should be partial hit -> overall False
            types3, hit3 = manager.get_types("part")
            self.assertFalse(hit3)
            self.assertEqual(len(types3), 2)

            # 5. Query again -> Hit
            types4, hit4 = manager.get_types("part")
            self.assertTrue(hit4)


if __name__ == "__main__":
    unittest.main()
