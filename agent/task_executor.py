"""
Task Executor
Orchestrates the LLM to perform coding tasks on the uploaded codebase.
Supports: code modification, bug fixing, refactoring, test generation, docs, etc.
"""

import json
import re
from typing import Callable, Dict, Any, Optional, Generator


SYSTEM_PROMPT = """You are an elite AI coding agent. Your job is to:
1. Understand the developer's codebase deeply.
2. Execute the requested task with precision.
3. Return ONLY the modified/generated file contents in the exact JSON format specified.
4. Provide a clear explanation of every change made.

## Output Format (MANDATORY)
You MUST respond with a JSON object in this exact structure:
```json
{
  "explanation": "Clear explanation of what was changed and why",
  "changes": {
    "filename.ext": "COMPLETE new file content here",
    "another_file.ext": "COMPLETE new file content here"
  }
}
```

Rules:
- The "changes" dict maps filename → COMPLETE file content (not just the changed parts)
- If you create a new file (e.g., tests, README), include it in "changes" with the new filename
- Never truncate code with "..." or "rest of file remains..."
- If no files need changing (e.g., a question), set "changes" to {}
- Always write clean, production-ready code
- Add comments where changes are made
"""


def _build_codebase_context(codebase: Dict[str, str], analysis: Optional[Dict], task: str) -> str:
    """Build a context string with relevant files for the task."""
    parts = []

    # Analysis summary
    if analysis:
        parts.append("## Codebase Analysis")
        parts.append(analysis.get("summary", ""))
        parts.append(f"Files: {', '.join(codebase.keys())}")
        parts.append("")

    # Include file contents — smart truncation for large codebases
    total_chars = sum(len(v) for v in codebase.values())
    MAX_CHARS = 40_000  # ~10k tokens

    parts.append("## Files")
    if total_chars <= MAX_CHARS:
        for fname, content in codebase.items():
            parts.append(f"\n### {fname}\n```\n{content}\n```")
    else:
        # Prioritize smaller files and files mentioned in the task
        task_lower = task.lower()
        scored = []
        for fname, content in codebase.items():
            score = len(content)  # smaller = higher priority (lower score)
            if any(kw in task_lower for kw in fname.lower().split(".")):
                score = 0  # boost files mentioned in task
            scored.append((score, fname, content))
        scored.sort()

        budget = MAX_CHARS
        for _, fname, content in scored:
            if len(content) <= budget:
                parts.append(f"\n### {fname}\n```\n{content}\n```")
                budget -= len(content)
            elif budget > 500:
                # Include truncated
                parts.append(f"\n### {fname} (truncated)\n```\n{content[:budget]}\n... [truncated]\n```")
                budget = 0
            if budget <= 0:
                remaining = [f for _, f, _ in scored if f not in "\n".join(parts)]
                if remaining:
                    parts.append(f"\n[{len(remaining)} more file(s) not shown due to context limit]")
                break

    return "\n".join(parts)


def _extract_json(text: str) -> Optional[Dict]:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    patterns = [
        r"```json\s*([\s\S]+?)\s*```",
        r"```\s*([\s\S]+?)\s*```",
        r"\{[\s\S]+\}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            candidate = match.group(1) if "```" in pattern else match.group(0)
            try:
                return json.loads(candidate.strip())
            except json.JSONDecodeError:
                continue

    return None


class TaskExecutor:
    """
    Executes developer tasks on a codebase using the Groq LLM.

    Parameters
    ----------
    codebase   : dict of filename → content
    analysis   : result from CodebaseAnalyzer.analyze()
    model      : Groq model ID
    temperature: LLM temperature
    max_tokens : max output tokens
    stream_fn  : streaming generator function (messages, model, temp, max_tokens) → Generator[str]
    full_fn    : non-streaming function       (messages, model, temp, max_tokens) → str
    """

    def __init__(
        self,
        codebase: Dict[str, str],
        analysis: Optional[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        stream_fn: Callable,
        full_fn: Callable,
    ):
        self.codebase = codebase
        self.analysis = analysis
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream_fn = stream_fn
        self.full_fn = full_fn

    def execute(self, task: str) -> Dict[str, Any]:
        """
        Execute a coding task.

        Returns
        -------
        {
            "explanation": str,
            "proposed_changes": {filename: new_content},
            "raw_response": str,
        }
        """
        context = _build_codebase_context(self.codebase, self.analysis, task)

        user_message = f"""## Developer Task
{task}

## Codebase
{context}

Remember: Respond ONLY with the JSON object as specified. Include COMPLETE file contents.
"""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Use non-streaming for task execution (need full JSON output)
        raw = self.full_fn(messages, self.model, self.temperature, self.max_tokens)

        # Parse response
        parsed = _extract_json(raw)

        if parsed and isinstance(parsed, dict):
            explanation = parsed.get("explanation", "Task completed.")
            changes = parsed.get("changes", {})
            # Validate that returned filenames exist or are new
            valid_changes = {
                k: v for k, v in changes.items()
                if isinstance(k, str) and isinstance(v, str) and v.strip()
            }
            return {
                "explanation": explanation,
                "proposed_changes": valid_changes,
                "raw_response": raw,
            }
        else:
            # Fallback: treat entire response as explanation
            return {
                "explanation": raw,
                "proposed_changes": {},
                "raw_response": raw,
            }
