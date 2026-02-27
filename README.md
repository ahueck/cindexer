# cindexer

A Python tool using `libclang` to parse C/C++ source files and extract user-defined types (structs, classes, enums, unions) and aliases (typedefs, usings).

## Project Components

- **`cindexer/`**: Core Python engine for C/C++ AST analysis.
- **`cindexer_python_ipc/`**: A Python client library for querying the state of a running VS Code instance.
- **`cindexer-vscode-extension/`**: A VS Code extension that publishes editor state (active file, compile commands, focus) for external tools.

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

### Extension Setup (`cindexer-vscode-extension`)
The extension enables bi-directional communication between VS Code and Python.

**Build & Install:**
1. `cd cindexer-vscode-extension`
2. `npm install && npm run compile`
3. Sideload the extension by copying the folder to your `.vscode/extensions` directory.

### Python IPC Client (`cindexer_python_ipc`)
A library to query the active VS Code state on demand.

**Usage:**
```python
from cindexer_python_ipc import VSCodeIPCClient
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
python3 cindexer_python_ipc/tests/query_state.py
```

### Automated Tests
- **Core Engine:** `lit -v tests/` (Requires `lit` and `FileCheck`)
- **IPC Library:** `python3 -m unittest cindexer_python_ipc/tests/test_ipc.py`

### Code Coverage (Core Engine)
To run tests with coverage reporting:

```bash
export CINDEXER_USE_COVERAGE=1
lit -j 1 -v tests/
python3 -m coverage combine tests/
python3 -m coverage report -m
```
Note: `-j 1` is recommended for `lit` to avoid race conditions when writing coverage data.
