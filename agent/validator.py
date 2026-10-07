"""
Validator & Execution Sandbox Engine
Provides syntax validation and automated unit test execution for python codebases.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, Any, List


def validate_codebase_syntax(files: Dict[str, str]) -> Dict[str, Any]:
    """
    Validates syntax across uploaded/generated source files.
    Returns syntax status per file and overall valid boolean.
    """
    results: List[Dict[str, Any]] = []
    has_errors = False

    for filename, content in files.items():
        ext = os.path.splitext(filename)[1].lower()
        file_res = {
            "file": filename,
            "valid": True,
            "error": None,
            "line": None,
        }

        if ext == ".py":
            try:
                ast.parse(content, filename=filename)
            except SyntaxError as se:
                file_res["valid"] = False
                file_res["error"] = str(se.msg)
                file_res["line"] = se.lineno
                has_errors = True
            except Exception as e:
                file_res["valid"] = False
                file_res["error"] = str(e)
                has_errors = True

        elif ext == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError as jde:
                file_res["valid"] = False
                file_res["error"] = f"JSON error: {jde.msg}"
                file_res["line"] = jde.lineno
                has_errors = True

        results.append(file_res)

    return {
        "all_valid": not has_errors,
        "files_checked": len(files),
        "details": results,
    }


def run_python_tests(files: Dict[str, str]) -> Dict[str, Any]:
    """
    Executes Python unittest discovery in an isolated temporary directory.
    Returns stdout, stderr, exit_code, and parsed summary.
    """
    python_files = {k: v for k, v in files.items() if k.endswith(".py")}
    if not python_files:
        return {
            "ran": False,
            "message": "No Python files found in codebase to run tests on.",
            "passed": False,
            "stdout": "",
            "stderr": "",
        }

    # Check if any test file exists (starts with test_ or ends with _test.py)
    test_files = [f for f in python_files if f.startswith("test_") or f.endswith("_test.py")]
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="agent_test_runner_")
    try:
        # Write all python files into temp_dir
        for fname, content in python_files.items():
            file_path = os.path.join(temp_dir, fname)
            # Create parent dirs if necessary (e.g. subfolders)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Run python unittest module
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", temp_dir, "-p", "*.py"]
        proc = subprocess.run(
            cmd,
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = proc.stdout + "\n" + proc.stderr
        success = proc.returncode == 0

        # Parse test metrics from stderr (unittest prints summary to stderr)
        summary = "Tests executed."
        if "OK" in output:
            summary = "✅ All tests passed successfully!"
        elif "FAILED" in output:
            summary = "❌ Tests failed with errors."

        return {
            "ran": True,
            "success": success,
            "exit_code": proc.returncode,
            "test_files": test_files,
            "summary": summary,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "ran": True,
            "success": False,
            "error": "Test execution timed out (limit: 10s).",
            "summary": "⏱️ Execution timed out.",
            "stdout": "",
            "stderr": "",
        }
    except Exception as e:
        return {
            "ran": False,
            "error": str(e),
            "summary": f"Execution error: {str(e)}",
            "stdout": "",
            "stderr": "",
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
