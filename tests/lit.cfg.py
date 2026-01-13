# flake8: noqa: F821
import os
import shutil
import sys
import lit.util
import lit.formats

config.name = "cindexer-testsuite"
config.suffixes = [".c", ".cpp", ".sh"]
config.excludes = ["cmake_project"]
config.test_format = lit.formats.ShTest(True)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tool_path = os.path.join(project_root, "cindex-pass.py")
python_exec = sys.executable


def find_tool(name):
    path = shutil.which(name)
    if path:
        return path
    return name


filecheck_path = find_tool("FileCheck")
cmake_path = find_tool("cmake")

# --- Configuration Toggle ---
# Check if the environment flag is present
use_coverage = os.environ.get("CINDEXER_USE_COVERAGE")

if use_coverage:
    executable_cmd = f"{python_exec} -m coverage run"
    config.environment["COVERAGE_PROCESS_START"] = os.path.join(
        project_root, ".coveragerc"
    )
    config.environment["COVERAGE_FILE"] = os.path.join(
        project_root, "tests", ".coverage"
    )
else:
    executable_cmd = python_exec

config.environment["PYTHONPATH"] = os.environ.get("PYTHONPATH", "")
config.environment["LD_LIBRARY_PATH"] = os.environ.get("LD_LIBRARY_PATH", "")

config.substitutions.append(("%dump_types", f'{executable_cmd} "{tool_path}"'))
config.substitutions.append(("%filecheck", f'"{filecheck_path}"'))
config.substitutions.append(("%cmake", f'"{cmake_path}"'))
