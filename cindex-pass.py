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
from clang.cindex import Index, CursorKind

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
        grouped = {}
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
        "clang_args",
        nargs=argparse.REMAINDER,
        help="Filename followed by Clang arguments",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    if not args.clang_args:
        print("Error: No input file specified.", file=sys.stderr)
        sys.exit(1)

    index = Index.create()
    tu = index.parse(None, args.clang_args)

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
