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
from typing import List, Set, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from clang.cindex import (
    Index,
    CursorKind,
    CompilationDatabase,
    CompilationDatabaseError,
)


@dataclass
class TypeInfo:
    """
    Holds structured information about a parsed type.
    Decouples data extraction from output formatting.
    """

    name: str
    usr: str
    kind: str
    category: str
    is_definition: bool
    filename: str
    line: int
    column: int
    tu_source: str

    @staticmethod
    def from_cursor(cursor, category: str, kind: str, tu_source: str) -> "TypeInfo":
        return TypeInfo(
            name=cursor.spelling,
            usr=cursor.get_usr(),
            kind=kind,
            category=category,
            is_definition=cursor.is_definition(),
            filename=cursor.location.file.name if cursor.location.file else "<unknown>",
            line=cursor.location.line,
            column=cursor.location.column,
            tu_source=tu_source,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "usr": self.usr,
            "kind": self.kind,
            "category": self.category,
            "is_definition": self.is_definition,
            "location": {
                "file": self.filename,
                "line": self.line,
                "column": self.column,
            },
            "tu_source": self.tu_source,
        }


@dataclass
class DependencyInfo:
    path: str
    mtime: float
    is_system: bool


@dataclass(frozen=True)
class CacheEntry:
    source_path: str
    compile_signature: Tuple[str, ...]
    source_mtime: float
    type_infos: List[TypeInfo]
    dependencies: Dict[str, DependencyInfo]


class TypeCollector:
    """
    Stateful visitor that traverses the AST to collect type information.
    """

    USER_DEFINED_KINDS = {
        CursorKind.STRUCT_DECL: "Struct",
        CursorKind.CLASS_DECL: "Class",
        CursorKind.UNION_DECL: "Union",
        CursorKind.ENUM_DECL: "Enum",
        CursorKind.CLASS_TEMPLATE: "TemplateClass",
    }

    ALIAS_KINDS = {
        CursorKind.TYPEDEF_DECL: "Typedef",
        CursorKind.TYPE_ALIAS_DECL: "Using",
    }

    def __init__(
        self,
        tu_source: str,
        exclude_system_headers: bool = False,
        system_paths: Optional[List[str]] = None,
    ):
        self.tu_source = tu_source
        self.collected_types: List[TypeInfo] = []
        self.exclude_system_headers = exclude_system_headers
        self.system_paths = system_paths or []

    def _get_category_and_kind(self, cursor) -> Tuple[Optional[str], Optional[str]]:
        if cursor.kind in self.USER_DEFINED_KINDS:
            return "UserDefined", self.USER_DEFINED_KINDS[cursor.kind]
        if cursor.kind in self.ALIAS_KINDS:
            return "Alias", self.ALIAS_KINDS[cursor.kind]
        return None, None

    def collect(self, cursor):
        """
        Traverse AST and populate collected_types list with TypeInfo objects.
        Extracts ALL named types without filtering.
        """
        if self.exclude_system_headers:
            # Check if in system header (libclang check)
            if cursor.location.is_in_system_header:
                return
            if cursor.location.file:
                # print(self.system_paths)
                filename = cursor.location.file.name
                for sys_path in self.system_paths:
                    if filename.startswith(sys_path):
                        return

        if cursor.location.file:
            category, kind = self._get_category_and_kind(cursor)

            if category and kind and cursor.spelling:
                self.collected_types.append(
                    TypeInfo.from_cursor(cursor, category, kind, self.tu_source)
                )

        for child in cursor.get_children():
            self.collect(child)


class TranslationUnitCache:
    """
    Manages caching of parsed translation units.
    Validates cache entries based on file modification times.
    """

    def __init__(self):
        self._cache: Dict[Tuple[str, Tuple[str, ...]], CacheEntry] = {}

    def get(self, source_path: str, signature: Tuple[str, ...]) -> Optional[CacheEntry]:
        key = (source_path, signature)
        entry = self._cache.get(key)
        if not entry:
            return None

        try:
            current_mtime = os.path.getmtime(source_path)
        except OSError:
            # Handle deleted file
            del self._cache[key]
            return None

        if current_mtime != entry.source_mtime:
            # Invalidate if modified
            del self._cache[key]
            return None

        for dep_path, dep_info in entry.dependencies.items():
            # Skip system headers per requirements
            if dep_info.is_system:
                continue

            try:
                dep_mtime = os.path.getmtime(dep_path)
                if dep_mtime != dep_info.mtime:
                    del self._cache[key]
                    return None
            except OSError:
                del self._cache[key]
                return None

        return entry

    def put(
        self,
        source_path: str,
        signature: Tuple[str, ...],
        type_infos: List[TypeInfo],
        dependencies: Dict[str, DependencyInfo],
    ):
        try:
            source_mtime = os.path.getmtime(source_path)
        except OSError:
            return

        entry = CacheEntry(
            source_path=source_path,
            compile_signature=signature,
            source_mtime=source_mtime,
            type_infos=type_infos,
            dependencies=dependencies,
        )
        self._cache[(source_path, signature)] = entry

    def clear(self):
        """Clears the entire cache."""
        self._cache.clear()

    def remove(self, source_path: str, signature: Tuple[str, ...]) -> bool:
        """
        Removes a specific entry from the cache.
        Returns True if the entry existed and was removed, False otherwise.
        """
        key = (source_path, signature)
        if key in self._cache:
            del self._cache[key]
            return True
        return False


class IndexManager:
    """
    Coordinates parsing, caching, and query-time filtering.
    """

    def __init__(self, project_root: str, build_dir: Optional[str] = None):
        self.project_root = os.path.abspath(project_root)
        self.index = Index.create()
        self.cache = TranslationUnitCache()
        self.args_resolver = CompilationArgsResolver(self.project_root)
        self.db_handler = DatabaseHandler(build_dir)

    def _resolve_signature(
        self, source_file: str, extra_args: Optional[List[str]]
    ) -> Tuple[str, ...]:
        db_args = self.db_handler.get_compile_args(source_file)
        full_args = (db_args or []) + (extra_args or [])
        return self.args_resolver.resolve(full_args, source_file)

    def get_types(
        self,
        source_file: str,
        extra_args: Optional[List[str]] = None,
        filter_opts: Optional[Dict] = None,
        ignore_cache: bool = False,
        exclude_system_headers: bool = False,
    ) -> Tuple[List[TypeInfo], bool]:
        resolved_files = self.db_handler.find_matching_files(source_file)

        if len(resolved_files) > 1:
            print(
                f"Ambiguous path '{source_file}' matched multiple files:",
                file=sys.stderr,
            )
            for f in resolved_files:
                print(f"  - {f}", file=sys.stderr)
            print(f"Processing all matches...", file=sys.stderr)

        all_types = []
        is_cache_hit = True

        for f in resolved_files:
            types, hit = self._get_types_single(
                f, extra_args, filter_opts, ignore_cache, exclude_system_headers
            )
            all_types.extend(types)
            if not hit:
                is_cache_hit = False

        return all_types, is_cache_hit

    def _get_types_single(
        self,
        source_file: str,
        extra_args: Optional[List[str]] = None,
        filter_opts: Optional[Dict] = None,
        ignore_cache: bool = False,
        exclude_system_headers: bool = False,
    ) -> Tuple[List[TypeInfo], bool]:
        source_file = os.path.abspath(source_file)

        # Include exclusion flag in signature to invalidate cache on change
        signature = self._resolve_signature(source_file, extra_args)
        if exclude_system_headers:
            signature = signature + ("--exclude-sys",)

        cached_entry = None
        if not ignore_cache:
            cached_entry = self.cache.get(source_file, signature)

        type_infos = []
        is_cache_hit = False

        if cached_entry:
            type_infos = cached_entry.type_infos
            is_cache_hit = True
        else:
            try:
                # Use resolved args for consistency; libclang ignores removed flags (-c, -o)
                # Parse args might contain the extra flag we appended, remove it for parsing
                parse_args = list(signature)
                if exclude_system_headers:
                    parse_args = parse_args[:-1]

                tu = self.index.parse(source_file, args=parse_args)
                if not tu:
                    raise Exception("TranslationUnit is None")

                system_paths = CompilationArgsResolver.extract_isystem_paths(tuple(parse_args))
                collector = TypeCollector(
                    source_file,
                    exclude_system_headers=exclude_system_headers,
                    system_paths=system_paths,
                )
                collector.collect(tu.cursor)
                type_infos = collector.collected_types

                dependencies: Dict[str, DependencyInfo] = {}
                for include in tu.get_includes():
                    path = os.path.abspath(include.include.name)
                    try:
                        mtime = os.path.getmtime(path)
                        # Treat headers outside project root as system (heuristic)
                        is_system = False
                        if not path.startswith(self.project_root):
                            is_system = True

                        dependencies[path] = DependencyInfo(
                            path=path, mtime=mtime, is_system=is_system
                        )
                    except OSError:
                        pass

                self.cache.put(source_file, signature, type_infos, dependencies)

            except Exception as e:
                print(f"Error parsing {source_file}: {e}", file=sys.stderr)
                return [], False

        if not filter_opts:
            return type_infos, is_cache_hit

        filtered = TypeFilter.filter(
            type_infos,
            filter_opts.get("scope", "main"),
            filter_opts.get("decls", "defs"),
            source_file,
            show_std=filter_opts.get("show_std", False),
        )
        return filtered, is_cache_hit

    def clear_cache(self) -> None:
        """Clears the entire translation unit cache."""
        self.cache.clear()

    def clear_cache_for_tu(
        self, source_file: str, extra_args: Optional[List[str]] = None
    ) -> bool:
        """
        Removes a specific translation unit from the cache.
        Requires the same source file and arguments used during parsing.
        Returns True if the entry was found and removed.
        """
        resolved_files = self.db_handler.find_matching_files(source_file)
        any_removed = False

        for f in resolved_files:
            abs_source = os.path.abspath(f)
            signature = self._resolve_signature(abs_source, extra_args)
            if self.cache.remove(abs_source, signature):
                any_removed = True

        return any_removed


class TypeFilter:
    """
    Applies query-time filters to a list of TypeInfo objects.
    """

    @staticmethod
    def filter(
        type_infos: List[TypeInfo],
        scope: str,
        decls: str,
        main_file: str,
        show_std: bool = False,
    ) -> List[TypeInfo]:
        filtered = []
        for info in type_infos:
            if info.name.startswith("_"):
                continue

            if not show_std and ("@N@std@" in info.usr or "N@__gnu_cxx@" in info.usr):
                continue

            if scope == "main":
                if info.filename != main_file:
                    continue

            if decls == "defs":
                if not info.is_definition:
                    continue

            filtered.append(info)
        return filtered


class Formatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def output(self, type_infos: List[TypeInfo], show_location: bool):
        pass


class TextFormatter(Formatter):
    """Output results in a human-readable, line-by-line format."""

    def output(self, type_infos: List[TypeInfo], show_location: bool):
        grouped = {"UserDefined": [], "Alias": []}
        for info in type_infos:
            grouped.setdefault(info.category, []).append(info)

        for category, items in grouped.items():
            print(f"--- {category} ---")
            if not items:
                print("  (None found)")
                continue

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
        if not show_location:
            for item in data:
                del item["location"]

        print(json.dumps(data, indent=2))


class CompilationArgsResolver:
    """
    Canonicalizes compilation arguments to ensure stable signatures.
    """

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)

    def resolve(self, args: List[str], source_file: str) -> Tuple[str, ...]:
        """
        Produces a canonical signature tuple of compile arguments.
        - Resolves relative paths in -I, -isystem to absolute.
        - Removes -o, -c, and the source file itself.
        - Preserves order of semantic flags.
        """
        canonical = []
        skip_next = False
        abs_source = os.path.abspath(source_file)

        for i, arg in enumerate(args):
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

            # Handle -I and -isystem, resolving relative paths
            # Also arg variation like: -I /path/ or -I/path/
            if arg.startswith("-I") or arg.startswith("-isystem"):
                if len(arg) > 2 and arg.startswith("-I"):
                    path = arg[2:]
                    abs_path = os.path.abspath(os.path.join(self.root_dir, path))
                    canonical.append(f"-I{abs_path}")
                    continue
                if arg in ["-I", "-isystem"]:
                    canonical.append(arg)
                    if i + 1 < len(args):
                        next_arg = args[i + 1]
                        abs_path = os.path.abspath(
                            os.path.join(self.root_dir, next_arg)
                        )
                        canonical.append(abs_path)
                        skip_next = True
                    continue

            canonical.append(arg)

        return tuple(canonical)

    @staticmethod
    def extract_isystem_paths(args: Tuple[str, ...]) -> List[str]:
        paths = []
        skip_next = False
        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue
            if arg == "-isystem":
                if i + 1 < len(args):
                    paths.append(args[i + 1])
                    skip_next = True
        return paths


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
        Returns raw arguments (excluding compiler binary) without filtering,
        as CompilationArgsResolver handles filtering and canonicalization.
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

        raw_args = list(cmds[0].arguments)

        return raw_args[1:]

    def find_matching_files(self, partial_path: str) -> List[str]:
        """
        Resolves a partial path to a list of absolute paths from the compilation database.
        Returns unique matching absolute paths.
        """
        if not self.db:
            if os.path.exists(partial_path):
                return [os.path.abspath(partial_path)]
            return [partial_path]

        # Optimization: If path is absolute, try direct lookup first
        if os.path.isabs(partial_path):
            try:
                cmds = self.db.getCompileCommands(partial_path)
                if cmds and len(cmds) > 0:
                    return [partial_path]
            except Exception:
                pass

            # If absolute path not found in DB, return it as is (fallback behavior)
            return [partial_path]

        matches = set()
        partial_path_norm = partial_path.strip()

        try:
            all_cmds = self.db.getAllCompileCommands()
        except Exception:
            # Fallback if getAllCompileCommands fails or is not available
            all_cmds = []

        if not all_cmds:
            if os.path.exists(partial_path):
                return [os.path.abspath(partial_path)]
            return [partial_path]

        for cmd in all_cmds:
            file_path = cmd.filename
            abs_file_path = os.path.abspath(file_path)

            if abs_file_path.endswith(partial_path_norm):
                if len(abs_file_path) == len(partial_path_norm):
                    matches.add(abs_file_path)
                elif abs_file_path[-(len(partial_path_norm) + 1)] == os.path.sep:
                    matches.add(abs_file_path)

        results = sorted(list(matches))

        if not results:
            if os.path.exists(partial_path):
                return [os.path.abspath(partial_path)]
            return [partial_path]

        return results


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
        "--show-std",
        action="store_true",
        help="Show standard library types (std:: namespace).",
    )

    parser.add_argument(
        "--location",
        action="store_true",
        help="Include file path and line number in output.",
    )

    parser.add_argument(
        "--exclude-system-headers",
        action="store_true",
        help="Exclude types from system headers (including -isystem paths).",
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

    project_root = os.getcwd()
    if args.build_dir:
        project_root = os.path.dirname(os.path.abspath(args.build_dir))

    manager = IndexManager(project_root=project_root, build_dir=args.build_dir)

    filter_opts = {
        "scope": args.scope,
        "decls": args.decls,
        "show_std": args.show_std,
    }

    try:
        type_infos, _ = manager.get_types(
            source_file=args.source_file,
            extra_args=args.clang_extra_args,
            filter_opts=filter_opts,
            exclude_system_headers=args.exclude_system_headers,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.user_def:
        formatter: Formatter
        if args.format == "json":
            formatter = JsonFormatter()
        else:
            formatter = TextFormatter()
        formatter.output(type_infos, args.location)


if __name__ == "__main__":
    main()
