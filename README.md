# cindexer

A Python tool using `libclang` to parse C/C++ source files and extract user-defined types (structs, classes, enums, unions) and aliases (typedefs, usings).

## Project Components

- **`cindexer/`**: Core Python engine for C/C++ AST analysis.
- **`cindexer_rpc/`**: A Python client library for querying the state of a running VS Code instance.
- **`cindexer_vscode/`**: A VS Code extension that publishes editor state (active file, compile commands, focus) for external tools.

---

## 1. Core CLI (`cindexer`)

### Requirements
* Python 3.12+
* LLVM/Clang (with `libclang` bindings)
* `pip install libclang`

### Usage
```bash
python3 -m cindexer --user-def main.cpp
```

| Flag                                 | Description                                       |
|--------------------------------------|---------------------------------------------------|
| `--user-def`                         | Enable dumping of user-defined types and aliases. |
| `--scope {main,all,non-sys,non-std}` | Filter output by scope (default: `main`).         |
| `--decls {defs,all}`                 | Filter by declaration type (default: `defs`).     |
| `--format {text,json}`               | Output format (default: `text`).                  |

---

## 2. VS Code Integration

### Extension Setup (`cindexer_vscode`)
The extension enables bi-directional communication between VS Code and Python.

**Requirements:**
* Node.js v22+

**Build & Install:**
1. `cd cindexer_vscode`
2. `npm install && npm run compile`
3. Sideload the extension by copying the folder to your `.vscode/extensions` directory.

### Python IPC Client (`cindexer_rpc`)
A library to query the active VS Code state on demand.

**Usage:**
```python
from cindexer_rpc import VSCodeIPCClient
client = VSCodeIPCClient()
state = client.get_current_state()
print(f"Active File: {state.active_file}")
print(f"Compile DB: {state.compilation_database_path}")
```
---

## 3. Tools & Testing

### Manual Verification Tool
Use this to verify your VS Code ↔ Python connection:
```bash
python3 cindexer_rpc/tests/query_state.py
```

### Automated Tests
- **Core Engine:** `lit -v cindexer/tests/` (Requires `lit` and `FileCheck`)
- **IPC Library:** `python3 -m unittest discover -s cindexer_rpc -t .`

### Code Coverage
To run tests with coverage reporting for both packages:
```bash
export CINDEXER_USE_COVERAGE=1
lit -j 1 -v cindexer/tests/
python3 -m coverage run --rcfile=.coveragerc -p -m unittest discover -s cindexer_rpc -t .
python3 -m coverage combine cindexer/tests/ .
python3 -m coverage report -m
```

Note: `-j 1` is recommended for `lit` to avoid race conditions when writing coverage data.
