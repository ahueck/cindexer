import os
import sys
from typing import List, Tuple
from clang.cindex import CompilationDatabase, CompilationDatabaseError


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
