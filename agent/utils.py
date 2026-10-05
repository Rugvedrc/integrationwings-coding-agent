"""
Utility helpers for the AI Coding Agent.
"""

import io
import zipfile
from typing import Dict


# ─── language from extension ──────────────────────────────────────────────────
_EXT_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".sh": "bash",
    ".sql": "sql",
    ".toml": "toml",
    ".xml": "xml",
    ".txt": "text",
}


def get_language_from_ext(filename: str) -> str:
    """Return the Streamlit/Pygments language identifier for a filename."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXT_MAP.get(ext, "text")


# ─── token approximation ──────────────────────────────────────────────────────
def count_tokens_approx(char_count: int) -> int:
    """Roughly estimate token count from character count (1 token ≈ 4 chars)."""
    return char_count // 4


# ─── in-memory zip ───────────────────────────────────────────────────────────
def zip_files_in_memory(files: Dict[str, str]) -> bytes:
    """Zip a dict of {filename: content} into an in-memory ZIP file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files.items():
            zf.writestr(fname, content.encode("utf-8"))
    buf.seek(0)
    return buf.read()


# ─── diff rendering helpers ───────────────────────────────────────────────────
def render_diff(original: str, proposed: str) -> str:
    """Return a unified diff string between two texts."""
    import difflib
    lines = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile="original",
        tofile="proposed",
        lineterm="",
    ))
    return "".join(lines)


# ─── code highlighting (stub for Streamlit native code block) ────────────────
def highlight_code(code: str, language: str = "python") -> str:
    """Return code as-is; Streamlit's st.code() handles highlighting natively."""
    return code
