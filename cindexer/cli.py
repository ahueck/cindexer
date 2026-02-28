import os
import sys
import argparse
from .manager import IndexManager
from .formatters import Formatter, JsonFormatter, TextFormatter


def parse_arguments():
    parser = argparse.ArgumentParser(description="Dump user-defined types and aliases from a C/C++ source file.")

    parser.add_argument(
        "--user-def",
        action="store_true",
        help="Enable dumping of user-defined types and typedefs/aliases",
    )

    parser.add_argument(
        "--scope",
        choices=["main", "all", "non-sys", "non-std"],
        default="main",
        help="Scope: 'main' (source file only), 'all' (includes all headers), 'non-sys' (all non-system headers), or 'non-std' (includes -isystem headers, but no std headers).",
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

    project_root = os.getcwd()
    if args.build_dir:
        project_root = os.path.dirname(os.path.abspath(args.build_dir))

    manager = IndexManager(project_root=project_root, build_dir=args.build_dir)

    # Map scope argument to internal exclusion logic and filter logic
    exclude_system_headers = False
    exclude_isystem = False
    filter_scope = "main"

    if args.scope == "main":
        # Only main file. We can exclude system headers traversal optimization.
        exclude_system_headers = True
        exclude_isystem = True
        filter_scope = "main"
    elif args.scope == "all":
        # Everything.
        exclude_system_headers = False
        exclude_isystem = False
        filter_scope = "all"
    elif args.scope == "non-sys":
        # Everything except system headers (libclang system + -isystem).
        exclude_system_headers = True
        exclude_isystem = True
        filter_scope = "all"
    elif args.scope == "non-std":
        # Everything except standard headers (libclang system), but includes -isystem.
        exclude_system_headers = True
        exclude_isystem = False
        filter_scope = "all"

    filter_opts = {
        "scope": filter_scope,
        "decls": args.decls,
    }

    try:
        type_infos, _ = manager.get_types(
            source_file=args.source_file,
            extra_args=args.clang_extra_args,
            filter_opts=filter_opts,
            exclude_system_headers=exclude_system_headers,
            exclude_isystem=exclude_isystem,
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
