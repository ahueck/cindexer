# RUN: %python %s

import unittest
import sys
import os
import time

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

        # First pass - should parse
        opts = {"scope": "all", "decls": "all"}
        args = ["-I", self.test_dir]

        types1 = manager.get_types(self.source_file, args, opts)
        self.assertEqual(len(types1), 2)  # HeaderStruct, MainStruct

        # Access cache directly to verify entry exists
        # We need to resolve the signature manually to check the key
        signature = manager.args_resolver.resolve(args, self.source_file)
        cached_entry = manager.cache.get(self.source_file, signature)
        self.assertIsNotNone(cached_entry)

        # Second pass - should hit cache
        # We can't easily mock the internal parse method currently.

        types2 = manager.get_types(self.source_file, args, opts)
        self.assertEqual(len(types2), 2)

        # Modify header
        time.sleep(1.1)  # Ensure mtime changes
        os.utime(self.header_file, None)

        # Should invalidate cache
        cached_entry_after_touch = manager.cache.get(self.source_file, signature)
        self.assertIsNone(cached_entry_after_touch)

        # Reparse
        types3 = manager.get_types(self.source_file, args, opts)
        self.assertEqual(len(types3), 2)

        # Verify it's back in cache
        cached_entry_new = manager.cache.get(self.source_file, signature)
        self.assertIsNotNone(cached_entry_new)
        self.assertNotEqual(cached_entry, cached_entry_new)


if __name__ == "__main__":
    unittest.main()
