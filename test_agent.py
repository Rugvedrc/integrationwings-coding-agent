"""
Comprehensive Integration & Unit Test Suite
AI Coding Agent | IntegrationWings Assignment
"""

import unittest
from fastapi.testclient import TestClient

from main import app
from agent.codebase_analyzer import CodebaseAnalyzer
from agent.sample_codebases import SAMPLE_PROJECTS
from agent.validator import validate_codebase_syntax, run_python_tests

client = TestClient(app)


class TestCodebaseAnalyzer(unittest.TestCase):
    def test_analyzer_structure(self):
        sample = {
            "main.py": "def main():\n    pass\n\nclass Config:\n    pass\n",
            "app.js": "function start() { return true; }\n"
        }
        analyzer = CodebaseAnalyzer(sample)
        res = analyzer.analyze()

        self.assertEqual(res["file_count"], 2)
        self.assertEqual(res["function_count"], 2)
        self.assertEqual(res["class_count"], 1)
        self.assertIn("Python", res["languages"])
        self.assertIn("JavaScript", res["languages"])


class TestValidator(unittest.TestCase):
    def test_syntax_valid(self):
        code = {"test.py": "x = 1\ndef foo():\n    return x\n"}
        res = validate_codebase_syntax(code)
        self.assertTrue(res["all_valid"])

    def test_syntax_invalid(self):
        code = {"test.py": "def broken_func(\n"}
        res = validate_codebase_syntax(code)
        self.assertFalse(res["all_valid"])

    def test_unittest_sandbox(self):
        code = {
            "utils.py": "def multiply(a, b):\n    return a * b\n",
            "test_utils.py": "import unittest\nfrom utils import multiply\n\nclass TestUtils(unittest.TestCase):\n    def test_multiply(self):\n        self.assertEqual(multiply(3, 4), 12)\n\nif __name__ == '__main__':\n    unittest.main()\n"
        }
        res = run_python_tests(code)
        self.assertTrue(res["ran"])
        self.assertTrue(res["success"])


class TestSampleCodebases(unittest.TestCase):
    def test_sample_projects_exist(self):
        self.assertIn("fastapi-user-api", SAMPLE_PROJECTS)
        self.assertIn("express-auth-service", SAMPLE_PROJECTS)
        self.assertIn("python-data-processor", SAMPLE_PROJECTS)
        for proj in SAMPLE_PROJECTS.values():
            self.assertIn("id", proj)
            self.assertIn("files", proj)
            self.assertGreater(len(proj["files"]), 0)


class TestAPIEndpoints(unittest.TestCase):
    def test_get_status(self):
        r = client.get("/api/status")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["default_model"], "llama-3.3-70b-versatile")

    def test_get_models(self):
        r = client.get("/api/models")
        self.assertEqual(r.status_code, 200)
        models = [m["id"] for m in r.json()["models"]]
        self.assertIn("llama-3.3-70b-versatile", models)
        self.assertIn("llama-3.1-8b-instant", models)

    def test_get_sample_projects(self):
        r = client.get("/api/sample-projects")
        self.assertEqual(r.status_code, 200)
        projects = r.json()["projects"]
        self.assertGreater(len(projects), 0)

    def test_get_specific_sample_project(self):
        r = client.get("/api/sample-projects/fastapi-user-api")
        self.assertEqual(r.status_code, 200)
        self.assertIn("files", r.json())

    def test_post_analyze(self):
        files = {"main.py": "def test(): pass\n"}
        r = client.post("/api/analyze", json={"files": files})
        self.assertEqual(r.status_code, 200)
        self.assertIn("syntax_validation", r.json())

    def test_post_validate_syntax(self):
        files = {"main.py": "x = 1\n"}
        r = client.post("/api/validate-syntax", json={"files": files})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["all_valid"])

    def test_post_run_tests(self):
        files = {
            "calc.py": "def add(a, b): return a + b\n",
            "test_calc.py": "import unittest\nfrom calc import add\nclass TestCalc(unittest.TestCase):\n    def test_add(self): self.assertEqual(add(1, 1), 2)\n"
        }
        r = client.post("/api/run-tests", json={"files": files})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["success"])

    def test_post_download_zip(self):
        files = {"app.py": "print('hello')\n"}
        r = client.post("/api/download", json={"files": files})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "application/zip")

    def test_post_execute_task_validation(self):
        r = client.post("/api/execute-task", json={"files": {}, "task": "Add tests"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
