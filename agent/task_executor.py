"""
Task Executor Engine
Orchestrates prompt construction, LLM tool execution on Groq, and JSON patch extraction.
"""
import json
import re
from typing import Optional, Dict, Any

from groq import Groq
from agent.validator import validate_codebase_syntax

SYSTEM_PROMPT = """You are an elite AI Coding Agent. Your role is to:

1. Carefully read and understand the developer's codebase.
2. Create a step-by-step plan outlining which files need changes and why.
3. Execute the requested coding task with precision.
4. Return your response ONLY in the exact JSON format below.

## MANDATORY Output Format
```json
{
  "plan": "Step-by-step plan: which files you will modify and what changes you will make",
  "explanation": "Clear explanation of all changes made and why",
  "changes": {
    "filename.ext": "COMPLETE new file content (never truncate with '...')",
    "new_file.ext": "COMPLETE content for any new files created"
  }
}
```

## Rules
- "changes" must contain COMPLETE file contents: not diffs, not snippets
- Never say "rest of file remains unchanged": always write the full file
- If no code changes are needed, set "changes" to {}
- Write clean, production-ready, well-commented code
- Always include the plan field: this shows your reasoning
"""

FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "deepseek-r1-distill-llama-70b",
]


def _call_with_fallback(client: Groq, messages: list, model: str, temperature: float, max_tokens: int) -> str:
    models = [model] + [m for m in FALLBACK_MODELS if m != model]
    last_err = None
    for m in models:
        try:
            resp = client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if any(k in err_str for k in ["404", "400", "decommissioned", "model_not_found", "not_found", "invalid_request_error"]):
                continue
            raise e
    raise last_err


def _build_context(codebase: dict, analysis: Optional[dict], task: str) -> str:
    parts = []

    if analysis:
        parts.append("## Codebase Overview")
        parts.append(analysis.get("summary", ""))
        parts.append(f"Files: {', '.join(codebase.keys())}\n")

    total_chars = sum(len(v) for v in codebase.values())
    MAX_CHARS = 40_000

    parts.append("## Source Files")
    if total_chars <= MAX_CHARS:
        for fname, content in codebase.items():
            parts.append(f"\n### {fname}\n```\n{content}\n```")
    else:
        task_lower = task.lower()
        scored = []
        for fname, content in codebase.items():
            score = len(content)
            name_lower = fname.lower().replace(".", " ").replace("/", " ").replace("_", " ")
            if any(w in task_lower for w in name_lower.split()):
                score = 0
            scored.append((score, fname, content))
        scored.sort()

        budget = MAX_CHARS
        shown = []
        for _, fname, content in scored:
            if len(content) <= budget:
                parts.append(f"\n### {fname}\n```\n{content}\n```")
                shown.append(fname)
                budget -= len(content)
            elif budget > 1000:
                parts.append(f"\n### {fname} (truncated)\n```\n{content[:budget]}\n# ... truncated\n```")
                budget = 0
            if budget <= 0:
                skipped = [f for _, f, _ in scored if f not in shown]
                if skipped:
                    parts.append(f"\n[{len(skipped)} file(s) omitted due to context limit: {', '.join(skipped)}]")
                break

    return "\n".join(parts)


def _extract_json(text: str) -> Optional[dict]:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    for pattern in [r"```json\s*([\s\S]+?)\s*```", r"```\s*([\s\S]+?)\s*```", r"\{[\s\S]+\}"]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            candidate = match.group(1) if "```" in pattern else match.group(0)
            try:
                return json.loads(candidate.strip())
            except json.JSONDecodeError:
                continue
    return None


class TaskExecutor:
    def __init__(self, codebase: dict, analysis: Optional[dict], client: Groq,
                 model: str, temperature: float, max_tokens: int):
        self.codebase = codebase
        self.analysis = analysis
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def execute(self, task: str) -> dict:
        context = _build_context(self.codebase, self.analysis, task)

        user_message = f"""## Developer Task
{task}

## Codebase
{context}

Important: Respond ONLY with the JSON object. Include COMPLETE file contents in "changes".
"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        raw = _call_with_fallback(self.client, messages, self.model, self.temperature, self.max_tokens)
        parsed = _extract_json(raw)

        if parsed and isinstance(parsed, dict):
            changes = {
                k: v for k, v in parsed.get("changes", {}).items()
                if isinstance(k, str) and isinstance(v, str) and v.strip()
            }

            merged = {**self.codebase, **changes}
            syntax_val = validate_codebase_syntax(merged)

            return {
                "plan": parsed.get("plan", ""),
                "explanation": parsed.get("explanation", "Task completed."),
                "proposed_changes": changes,
                "syntax_validation": syntax_val,
                "raw_response": raw,
            }

        return {
            "plan": "",
            "explanation": raw,
            "proposed_changes": {},
            "syntax_validation": {"all_valid": True, "files_checked": 0, "details": []},
            "raw_response": raw,
        }
