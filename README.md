# cindexer

A Python tool using `libclang` to parse C/C++ source files and dump user-defined types (structs, classes, enums, unions) and aliases (typedefs, usings). It supports JSON/Text output.

## Requirements

* Python 3+
* LLVM/Clang installed (with `libclang`)
* `pip install libclang` (Python bindings)

## Environment Setup

Ensure Python can find the `cindex` bindings and the `libclang` shared library.

```bash
export PYTHONPATH=/usr/lib/llvm-21/lib/python3.10/site-packages:$PYTHONPATH
export LD_LIBRARY_PATH=/usr/lib/llvm-21/lib:$LD_LIBRARY_PATH
```

## Usage

### Basic Execution

Dump types defined in `main.cpp` to stdout:

```bash
python3 cindex-pass.py --user-def main.cpp
```

### Options

| Flag                   | Description                                                                      |
|------------------------|----------------------------------------------------------------------------------|
| `--user-def`           | Enable dumping of user-defined types and aliases.                                |
| `--scope {main,all}`   | `main` (default): Only types in the source file. `all`: Includes system headers. |
| `--decls {defs,all}`   | `defs` (default): Only definitions. `all`: Includes forward declarations.        |
| `--format {text,json}` | Output format. Default is `text`.                                                |
| `--location`           | Include file path and line numbers in text output.                               |

### Advanced Examples

**JSON Output:**

```bash
python3 cindex-pass.py --user-def --format=json source.cpp
```

**Include Forward Declarations:**

```bash
python3 cindex-pass.py --user-def --decls=all source.cpp
```

**Pass Compiler Flags:**

```bash
python3 cindex-pass.py --user-def source.cpp -- -I/usr/local/include -std=c++17
```

## Testing

The test suite parses requirements 
- llvm-lit: `pip install lit`.
- FileCheck
- CMake

```bash
lit -v tests/
```
