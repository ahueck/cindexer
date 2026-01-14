#!/usr/bin/env python3

"""
A simple command line tool for dumping a source file infos using the Clang Index
Library.
"""

import sys
import argparse
import json
import os
from abc import ABC, abstractmethod
from typing import List, Set, Dict, Any
from clang.cindex import (
    Index,
    CursorKind,
    CompilationDatabase,
    CompilationDatabaseError,
)

# --- Constants ---

USER_DEFINED_KINDS = {
    CursorKind.STRUCT_DECL: "Struct",
    CursorKind.CLASS_DECL: "Class",
    CursorKind.UNION_DECL: "Union",
    CursorKind.ENUM_DECL: "Enum",
    CursorKind.CLASS_TEMPLATE: "TemplateClass",
}

ALIAS_KINDS = {CursorKind.TYPEDEF_DECL: "Typedef", CursorKind.TYPE_ALIAS_DECL: "Using"}

# --- Data Objects ---


class TypeInfo:
    """
    Holds structured information about a parsed type.
    Decouples data extraction from output formatting.
    """

    def __init__(self, cursor, category: str):
        self.name = cursor.spelling
        self.kind = self._get_readable_kind(cursor)
        self.category = category  # 'UserDefined' or 'Alias'
        self.is_definition = cursor.is_definition()
        self.filename = (
            cursor.location.file.name if cursor.location.file else "<unknown>"
        )
        self.line = cursor.location.line
        self.column = cursor.location.column

    def _get_readable_kind(self, cursor) -> str:
        if cursor.kind in USER_DEFINED_KINDS:
            return USER_DEFINED_KINDS[cursor.kind]
        if cursor.kind in ALIAS_KINDS:
            return ALIAS_KINDS[cursor.kind]
        return str(cursor.kind)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "kind": self.kind,
            "category": self.category,
            "is_definition": self.is_definition,
            "location": {
                "file": self.filename,
                "line": self.line,
                "column": self.column,
            },
        }


# --- Formatters ---


class Formatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def output(self, type_infos: List[TypeInfo], show_location: bool):
        pass


class TextFormatter(Formatter):
    """Output results in a human-readable, line-by-line format."""

    def output(self, type_infos: List[TypeInfo], show_location: bool):
        # Group by category for cleaner display
        grouped = {"UserDefined": [], "Alias": []}
        for info in type_infos:
            grouped.setdefault(info.category, []).append(info)

        for category, items in grouped.items():
            print(f"--- {category} ---")
            if not items:
                print("  (None found)")
                continue

            # Sort by name for readability
            for item in sorted(items, key=lambda x: x.name):
                loc_str = ""
                if show_location:
                    loc_str = f" @ {item.filename}:{item.line}"

                def_str = "[Def]" if item.is_definition else "[Decl]"
                print(f"  {item.kind}: {item.name} {def_str}{loc_str}")
            print("")


class JsonFormatter(Formatter):
    """Output results as a generic JSON object."""

    def output(self, type_infos: List[TypeInfo], show_location: bool):
        data = [t.to_dict() for t in type_infos]
        # If user strictly requested NO location in JSON, we strip it out.
        if not show_location:
            for item in data:
                del item["location"]

        print(json.dumps(data, indent=2))


# --- Logic ---


def should_process_cursor(cursor, tu, scope_mode) -> bool:
    if scope_mode == "all":
        return True
    if not cursor.location.file:
        return False
    return cursor.location.file.name == tu.spelling


def should_record_decl(cursor, decl_mode) -> bool:
    if decl_mode == "all":
        return True
    return cursor.is_definition()


def collect_types(cursor, collected_types: List[TypeInfo], tu, args):
    """
    Traverse AST and populate collected_types list with TypeInfo objects.
    """
    if should_process_cursor(cursor, tu, args.scope):
        category = None
        if cursor.kind in USER_DEFINED_KINDS:
            category = "UserDefined"
        elif cursor.kind in ALIAS_KINDS:
            category = "Alias"

        if category and cursor.spelling:
            if should_record_decl(cursor, args.decls):
                collected_types.append(TypeInfo(cursor, category))

    for child in cursor.get_children():
        collect_types(child, collected_types, tu, args)


# --- CDB ---


class DatabaseHandler:
    def __init__(self, build_path=None):
        self.db = None
        if build_path:
            try:
                self.db = CompilationDatabase.fromDirectory(build_path)
                print(f"Loaded compilation database from: {build_path}")
            except CompilationDatabaseError:
                print(
                    f"Warning: Could not load compilation database from {build_path}",
                    file=sys.stderr,
                )

    def _find_db_upwards(self, source_file):
        """Walks up the directory tree looking for compile_commands.json"""
        d = os.path.dirname(os.path.abspath(source_file))
        root = os.path.abspath(os.sep)

        while d != root:
            if os.path.exists(os.path.join(d, "compile_commands.json")):
                return d
            if os.path.exists(os.path.join(d, "build", "compile_commands.json")):
                return os.path.join(d, "build")
            d = os.path.dirname(d)
        return None

    def get_compile_args(self, source_file):
        """
        Returns a list of compiler arguments for the given file.
        Prioritizes the loaded DB. Falls back to auto-detection.
        """
        abs_source = os.path.abspath(source_file)
        if not self.db:
            found_path = self._find_db_upwards(abs_source)
            if found_path:
                print(f"Auto-detected compilation database at: {found_path}")
                try:
                    self.db = CompilationDatabase.fromDirectory(found_path)
                except CompilationDatabaseError:
                    pass  # Silently fail auto-detection and fallback to defaults
        if not self.db:
            return []
        cmds = self.db.getCompileCommands(abs_source)
        if cmds is None or len(cmds) == 0:
            print(
                f"Warning: File '{source_file}' not found in compilation database.",
                file=sys.stderr,
            )
            return []

        # The .arguments list, e.g.: ['/usr/bin/c++', '-DDEF', '-c', 'file.cpp', '-o', 'file.o']
        raw_args = list(cmds[0].arguments)

        cleaned_args = []
        skip_next = False

        for arg in raw_args[1:]:
            if skip_next:
                skip_next = False
                continue
            if arg == "-o":
                skip_next = True
                continue
            if arg == "-c":
                continue
            if arg == source_file or os.path.abspath(arg) == abs_source:
                continue
            cleaned_args.append(arg)

        return cleaned_args


# --- Main ---


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Dump user-defined types and aliases from a C/C++ source file."
    )

    parser.add_argument(
        "--user-def",
        action="store_true",
        help="Enable dumping of user-defined types and typedefs/aliases",
    )

    parser.add_argument(
        "--scope",
        choices=["main", "all"],
        default="main",
        help="Scope: 'main' (source file only) or 'all' (includes headers).",
    )

    parser.add_argument(
        "--decls",
        choices=["defs", "all"],
        default="defs",
        help="'defs' (only definitions) or 'all' (includes forward decls).",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="json",
        help="Output format. Default: json",
    )

    parser.add_argument(
        "--location",
        action="store_true",
        help="Include file path and line number in output.",
    )

    parser.add_argument(
        "-p",
        "--build-dir",
        help="Path to the build directory containing compile_commands.json",
    )

    parser.add_argument("source_file", help="The source file to parse")

    parser.add_argument(
        "clang_extra_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments to pass to Clang",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    db_handler = DatabaseHandler(args.build_dir)
    db_args = db_handler.get_compile_args(args.source_file)

    # index = Index.create()
    # tu = index.parse(None, args.clang_args)
    index = Index.create()
    try:
        tu = index.parse(args.source_file, args=db_args or args.clang_extra_args)
    except Exception:
        tu = None

    if not tu:
        print("Error: Unable to load input.", file=sys.stderr)
        sys.exit(1)

    if args.user_def:
        collected_data: List[TypeInfo] = []
        collect_types(tu.cursor, collected_data, tu, args)

        formatter: Formatter
        if args.format == "json":
            formatter = JsonFormatter()
        else:
            formatter = TextFormatter()
        formatter.output(collected_data, args.location)


if __name__ == "__main__":
    main()
