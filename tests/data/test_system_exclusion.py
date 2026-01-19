# RUN: %python %s

import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Load cindexer module
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)
import cindexer as cindex_pass

TypeCollector = cindex_pass.TypeCollector
CompilationArgsResolver = cindex_pass.CompilationArgsResolver


class TestSystemHeaderExclusion(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_extract_isystem_paths(self):
        args = ("-I/foo", "-isystem", "/sys/inc", "-DDEBUG", "-isystem", "/sys/inc2")
        paths = CompilationArgsResolver.extract_isystem_paths(args)
        self.assertEqual(paths, ["/sys/inc", "/sys/inc2"])

        args_no_sys = ("-I/foo", "-DDEBUG")
        paths_no = CompilationArgsResolver.extract_isystem_paths(args_no_sys)
        self.assertEqual(paths_no, [])

    def test_collector_exclude_isystem(self):
        # Mock cursor hierarchy
        mock_tu_cursor = MagicMock()
        mock_tu_cursor.location.is_in_system_header = False
        mock_tu_cursor.location.file.name = "/src/main.c"
        mock_tu_cursor.kind = "TRANSLATION_UNIT"
        mock_tu_cursor.spelling = "main.c"

        # Child in system path
        sys_child = MagicMock()
        sys_child.location.is_in_system_header = False  # pretending libclang missed it
        sys_child.location.file.name = "/sys/inc/header.h"
        sys_child.kind = cindex_pass.CursorKind.STRUCT_DECL
        sys_child.spelling = "SysStruct"

        # Child in user path
        user_child = MagicMock()
        user_child.location.is_in_system_header = False
        user_child.location.file.name = "/src/user.h"
        user_child.kind = cindex_pass.CursorKind.STRUCT_DECL
        user_child.spelling = "UserStruct"

        mock_tu_cursor.get_children.return_value = [sys_child, user_child]
        # Children have no children
        sys_child.get_children.return_value = []
        user_child.get_children.return_value = []

        # Test WITH exclusion
        collector = TypeCollector(
            "/src/main.c", exclude_system_headers=True, system_paths=["/sys/inc"]
        )
        collector.collect(mock_tu_cursor)

        # Should only find UserStruct
        names = [t.name for t in collector.collected_types]
        self.assertIn("UserStruct", names)
        self.assertNotIn("SysStruct", names)

        # Test WITHOUT exclusion
        collector_no = TypeCollector(
            "/src/main.c", exclude_system_headers=False, system_paths=["/sys/inc"]
        )
        collector_no.collect(mock_tu_cursor)

        names_no = [t.name for t in collector_no.collected_types]
        self.assertIn("UserStruct", names_no)
        self.assertIn("SysStruct", names_no)

    def test_collector_exclude_libclang_flag(self):
        # Child marked as system header by libclang
        sys_child = MagicMock()
        sys_child.location.is_in_system_header = True
        sys_child.location.file.name = "/usr/include/stdlib.h"
        sys_child.kind = cindex_pass.CursorKind.STRUCT_DECL
        sys_child.spelling = "DivT"

        mock_tu_cursor = MagicMock()
        mock_tu_cursor.location.file.name = "/src/main.c"
        mock_tu_cursor.get_children.return_value = [sys_child]
        sys_child.get_children.return_value = []

        collector = TypeCollector("/src/main.c", exclude_system_headers=True)
        collector.collect(mock_tu_cursor)

        self.assertEqual(len(collector.collected_types), 0)

    def test_collector_accurate_path_matching(self):
        # Child in a directory that starts with the same prefix as a system path
        # but is not actually in that directory.
        # e.g. sys_path = "/usr/include", filename = "/usr/include_extra/header.h"

        sys_path = "/usr/include"
        overlap_file = "/usr/include_extra/header.h"

        mock_tu_cursor = MagicMock()
        mock_tu_cursor.location.is_in_system_header = False
        mock_tu_cursor.location.file.name = "/src/main.c"
        mock_tu_cursor.kind = "TRANSLATION_UNIT"

        overlap_child = MagicMock()
        overlap_child.location.is_in_system_header = False
        overlap_child.location.file.name = overlap_file
        overlap_child.kind = cindex_pass.CursorKind.STRUCT_DECL
        overlap_child.spelling = "OverlapStruct"

        mock_tu_cursor.get_children.return_value = [overlap_child]
        overlap_child.get_children.return_value = []

        # Test WITH exclusion of /usr/include
        collector = TypeCollector(
            "/src/main.c", exclude_system_headers=True, system_paths=[sys_path]
        )
        collector.collect(mock_tu_cursor)

        # OverlapStruct should STILL be collected because /usr/include_extra is not /usr/include
        names = [t.name for t in collector.collected_types]
        self.assertIn("OverlapStruct", names)


if __name__ == "__main__":
    unittest.main()
