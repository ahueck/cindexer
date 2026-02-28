import os
import sys
from typing import List, Dict, Optional, Tuple
from clang.cindex import Index
from .models import TypeInfo, DependencyInfo
from .collector import TypeCollector
from .cache import TranslationUnitCache
from .filter import TypeFilter
from .utils import CompilationArgsResolver, DatabaseHandler


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

    def _resolve_signature(self, source_file: str, extra_args: Optional[List[str]]) -> Tuple[str, ...]:
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
        exclude_isystem: bool = False,
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
                f,
                extra_args,
                filter_opts,
                ignore_cache,
                exclude_system_headers,
                exclude_isystem,
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
        exclude_isystem: bool = False,
    ) -> Tuple[List[TypeInfo], bool]:
        source_file = os.path.abspath(source_file)

        # Include exclusion flag in signature to invalidate cache on change
        signature = self._resolve_signature(source_file, extra_args)
        if exclude_system_headers:
            signature = signature + ("--exclude-sys",)
        if exclude_isystem:
            signature = signature + ("--exclude-isys",)

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
                # Filter out internal tracking flags from the signature before passing to libclang
                internal_flags = {"--exclude-sys", "--exclude-isys"}
                parse_args = [arg for arg in signature if arg not in internal_flags]

                tu = self.index.parse(source_file, args=parse_args)
                if not tu:
                    raise Exception("TranslationUnit is None")

                system_paths = []
                if exclude_isystem:
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

                        dependencies[path] = DependencyInfo(path=path, mtime=mtime, is_system=is_system)
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
        )
        return filtered, is_cache_hit

    def clear_cache(self) -> None:
        """Clears the entire translation unit cache."""
        self.cache.clear()

    def clear_cache_for_tu(self, source_file: str, extra_args: Optional[List[str]] = None) -> bool:
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
