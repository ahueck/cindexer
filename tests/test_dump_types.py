import unittest
import subprocess
import sys
import os
import glob
from pathlib import Path

# Paths
TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"
TOOL_PATH = (TEST_DIR.parent / "cindex-pass.py").resolve()


class TestDumpTypesFileCheck(unittest.TestCase):
    """
    Runs the dump_types tool against C/C++ files in tests/data/
    and verifies output against comments in the source file.
    """

    def run_tool(self, filepath):
        """Runs the tool and returns stdout."""
        cmd = [
            sys.executable,
            str(TOOL_PATH),
            "--user-def",  # Enable user-defined types
            "--format=text",  # Use text format for easier string matching
            str(filepath),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_all_data_files(self):
        """
        Dynamic test that iterates over all .c and .cpp files in tests/data.
        """
        test_files = list(DATA_DIR.glob("*.c")) + list(DATA_DIR.glob("*.cpp"))

        if not test_files:
            self.fail(f"No test files found in {DATA_DIR}")

        for test_file in test_files:
            with self.subTest(file=test_file.name):
                self.verify_file(test_file)

    def verify_file(self, filepath):
        """
        1. Parse the file for '// CHECK: expected_string' lines.
        2. Run the tool.
        3. Assert all expected strings are present in the output.
        """
        expected_lines = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if "// CHECK:" in line:
                    # Extract text after CHECK:
                    expected = line.split("// CHECK:", 1)[1].strip()
                    if expected:
                        expected_lines.append(expected)

        if not expected_lines:
            self.skipTest(f"No CHECK markers found in {filepath.name}")

        result = self.run_tool(filepath)
        self.assertEqual(
            result.returncode,
            0,
            f"Tool crashed on {filepath.name}\nStderr: {result.stderr}",
        )
        output = result.stdout

        for expect in expected_lines:
            self.assertIn(
                expect,
                output,
                f"\nFile: {filepath.name}\n"
                f"Missing Expected Output: '{expect}'\n"
                f"Actual Output:\n{output}",
            )


if __name__ == "__main__":
    unittest.main()
