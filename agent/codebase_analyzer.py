"""
Codebase Analyzer
Parses uploaded source files to extract structure, stats, and a summary.
"""

import re
import os
from typing import Dict, Any
from collections import Counter


# Extension → language mapping
EXT_TO_LANG: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React (JSX)",
    ".tsx": "React (TSX)",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".txt": "Text",
    ".toml": "TOML",
    ".sh": "Shell",
    ".sql": "SQL",
}

# Regex patterns for function/class detection per language
PATTERNS = {
    "Python": {
        "function": re.compile(r"^\s*def\s+(\w+)\s*\(", re.MULTILINE),
        "class": re.compile(r"^\s*class\s+(\w+)", re.MULTILINE),
        "import": re.compile(r"^\s*(?:import|from)\s+(\S+)", re.MULTILINE),
    },
    "JavaScript": {
        "function": re.compile(r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*(?:async\s*)?function)", re.MULTILINE),
        "class": re.compile(r"class\s+(\w+)", re.MULTILINE),
        "import": re.compile(r"^import\s+.+\s+from\s+['\"](.+)['\"]", re.MULTILINE),
    },
    "TypeScript": {
        "function": re.compile(r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\()", re.MULTILINE),
        "class": re.compile(r"class\s+(\w+)", re.MULTILINE),
        "import": re.compile(r"^import\s+.+\s+from\s+['\"](.+)['\"]", re.MULTILINE),
    },
    "Java": {
        "function": re.compile(r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(", re.MULTILINE),
        "class": re.compile(r"(?:class|interface|enum)\s+(\w+)", re.MULTILINE),
        "import": re.compile(r"^import\s+([\w.]+)", re.MULTILINE),
    },
    "Go": {
        "function": re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", re.MULTILINE),
        "class": re.compile(r"type\s+(\w+)\s+struct", re.MULTILINE),
        "import": re.compile(r'"([\w./]+)"', re.MULTILINE),
    },
}


class CodebaseAnalyzer:
    """Analyzes a dict of {filename: content} and returns structured metadata."""

    def __init__(self, codebase: Dict[str, str]):
        self.codebase = codebase

    def analyze(self) -> Dict[str, Any]:
        languages: Counter = Counter()
        total_lines = 0
        total_chars = 0
        function_count = 0
        class_count = 0
        all_imports: list = []
        file_details: list = []

        for filename, content in self.codebase.items():
            ext = os.path.splitext(filename)[1].lower()
            lang = EXT_TO_LANG.get(ext, "Unknown")
            lines = content.count("\n") + 1
            chars = len(content)

            languages[lang] += 1
            total_lines += lines
            total_chars += chars

            # Per-language analysis
            patterns = PATTERNS.get(lang, {})
            fn_matches = patterns.get("function", re.compile("$^")).findall(content)
            cls_matches = patterns.get("class", re.compile("$^")).findall(content)
            imp_matches = patterns.get("import", re.compile("$^")).findall(content)

            # Flatten multi-group matches
            fns = [m if isinstance(m, str) else next((x for x in m if x), "") for m in fn_matches]
            fns = [f for f in fns if f]
            clss = [m if isinstance(m, str) else next((x for x in m if x), "") for m in cls_matches]
            clss = [c for c in clss if c]

            function_count += len(fns)
            class_count += len(clss)
            all_imports.extend(imp_matches)

            file_details.append({
                "file": filename,
                "language": lang,
                "lines": lines,
                "functions": fns[:10],   # top 10
                "classes": clss[:5],
                "imports": imp_matches[:5],
            })

        # Build a textual summary
        top_langs = ", ".join(f"{lang} ({cnt})" for lang, cnt in languages.most_common(5))
        summary_lines = [
            f"**Languages:** {top_langs}",
            f"**Total lines:** {total_lines:,} across {len(self.codebase)} file(s)",
            f"**Functions found:** {function_count} | **Classes/Types:** {class_count}",
        ]
        if function_count > 0:
            all_fns = []
            for fd in file_details:
                all_fns.extend(fd["functions"])
            summary_lines.append(f"**Sample functions:** {', '.join(f'`{f}`' for f in all_fns[:8])}")

        # Entry point detection
        entry_points = [f for f in self.codebase if f in ("main.py", "app.py", "index.js", "index.ts", "main.go", "App.tsx", "server.py")]
        if entry_points:
            summary_lines.append(f"**Entry points:** {', '.join(f'`{e}`' for e in entry_points)}")

        return {
            "file_count": len(self.codebase),
            "total_lines": total_lines,
            "total_chars": total_chars,
            "languages": dict(languages),
            "function_count": function_count,
            "class_count": class_count,
            "file_details": file_details,
            "summary": "\n".join(summary_lines),
            "common_imports": Counter(
                i if isinstance(i, str) else (i[0] if i else "")
                for i in all_imports
            ).most_common(10),
        }
