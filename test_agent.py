"""
Unit Tests for AI Coding Agent Backend & Agent Modules
IntegrationWings Assignment
"""

import unittest
from agent.codebase_analyzer import CodebaseAnalyzer
from agent.sample_codebases import SAMPLE_PROJECTS
from agent.validator import validate_codebase_syntax, run_python_tests


class TestCodebaseAnalyzer(unittest.TestCase):
    def test_analyzer_basic(self):
        sample = {
            "main.py": "def foo():\n    pass\n\nclass Bar:\n    pass\n",
            "utils.js": "function hello() { return 'world'; }\n"
        }
        analyzer = CodebaseAnalyzer(sample)
        result = analyzer.analyze()

        self.assertEqual(result["file_count"], 2)
        self.assertEqual(result["function_count"], 2)
        self.assertEqual(result["class_count"], 1)
        self.assertIn("Python", result["languages"])
        self.assertIn("JavaScript", result["languages"])

    def test_sample_codebases(self):
        self.assertIn("fastapi-user-api", SAMPLE_PROJECTS)
        self.assertIn("express-auth-service", SAMPLE_PROJECTS)
        self.assertIn("python-data-processor", SAMPLE_PROJECTS)

    def test_validator_syntax(self):
        valid_code = {"app.py": "x = 10\ndef run():\n    return x\n"}
        res = validate_codebase_syntax(valid_code)
        self.assertTrue(res["all_valid"])

        invalid_code = {"app.py": "def broken_func(\n"}
        res_invalid = validate_codebase_syntax(invalid_code)
        self.assertFalse(res_invalid["all_valid"])

    def test_run_python_tests(self):
        codebase = {
            "math_utils.py": "def add(a, b):\n    return a + b\n",
            "test_math.py": "import unittest\nfrom math_utils import add\n\nclass TestMath(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\nif __name__ == '__main__':\n    unittest.main()\n"
        }
        res = run_python_tests(codebase)
        self.assertTrue(res["ran"])
        self.assertTrue(res["success"])
        self.assertIn("test_math.py", res["test_files"])


if __name__ == "__main__":
    unittest.main()
