# flake8: noqa: F821
import os
import shutil
import sys
import lit.util
import lit.formats

config.name = "cindexer-tsestsuite"
config.suffixes = [".c", ".cpp", '.sh']
config.excludes = ['cmake_project']
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

config.environment["PYTHONPATH"] = os.environ.get("PYTHONPATH", "")
config.environment["LD_LIBRARY_PATH"] = os.environ.get("LD_LIBRARY_PATH", "")

config.substitutions.append(("%dump_types", f'"{python_exec}" "{tool_path}"'))
config.substitutions.append(("%filecheck", f'"{filecheck_path}"'))
config.substitutions.append(('%cmake', f'"{cmake_path}"'))
