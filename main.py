"""
AI Coding Agent: FastAPI Backend
IntegrationWings Assignment
"""
import io
import json
import os
import re
import zipfile
from typing import AsyncGenerator, Optional, Dict, Any, List

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
from pydantic import BaseModel

from agent.codebase_analyzer import CodebaseAnalyzer
from agent.task_executor import TaskExecutor
from agent.sample_codebases import SAMPLE_PROJECTS
from agent.validator import validate_codebase_syntax, run_python_tests
from agent.utils import zip_files_in_memory

# ─── setup ──────────────────────────────────────────────────────────────────
load_dotenv()

app = FastAPI(title="AI Coding Agent", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Groq setup ──────────────────────────────────────────────────────────────
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "deepseek-r1-distill-llama-70b",
]

DEFAULT_MODEL = "llama-3.3-70b-versatile"


def get_groq_client(api_key: Optional[str] = None) -> Groq:
    key = api_key or os.getenv("GROQ_API_KEY", "")
    if not key:
        raise HTTPException(
            status_code=400,
            detail="No GROQ_API_KEY found. Set it in environment variables or configure it in Settings."
        )
    return Groq(api_key=key)


def call_groq(client: Groq, messages: list, model: str, temperature: float, max_tokens: int) -> str:
    models = [model] + [m for m in FALLBACK_MODELS if m != model]
    seen = set()
    unique_models = []
    for m in models:
        if m and m not in seen:
            seen.add(m)
            unique_models.append(m)

    last_err = None
    for m in unique_models:
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
            if "401" in err_str or "invalid_api_key" in err_str or "unauthorized" in err_str:
                raise Exception("Invalid Groq API key. Please check your GROQ_API_KEY in environment or Settings.") from e
            continue
    raise Exception(f"AI Service Error: {str(last_err)}")


async def stream_groq(client: Groq, messages: list, model: str, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
    models = [model] + [m for m in FALLBACK_MODELS if m != model]
    seen = set()
    unique_models = []
    for m in models:
        if m and m not in seen:
            seen.add(m)
            unique_models.append(m)

    for m in unique_models:
        try:
            stream = client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "invalid_api_key" in err_str or "unauthorized" in err_str:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Invalid Groq API key.'})}\n\n"
                return
            continue
    yield f"data: {json.dumps({'type': 'error', 'content': 'No working LLM model found.'})}\n\n"


# ─── request / response models ───────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    files: Dict[str, str]


class TaskRequest(BaseModel):
    files: Dict[str, str]
    analysis: Optional[Dict[str, Any]] = None
    task: str
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 8192
    api_key: Optional[str] = None


class AuditRequest(BaseModel):
    files: Dict[str, str]
    model: str = DEFAULT_MODEL
    api_key: Optional[str] = None


class RunTestsRequest(BaseModel):
    files: Dict[str, str]


class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    files_summary: str = ""
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 4096
    api_key: Optional[str] = None


class DownloadRequest(BaseModel):
    files: Dict[str, str]


# ─── routes ──────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def status():
    api_key = os.getenv("GROQ_API_KEY", "")
    return {
        "ok": True,
        "api_key_configured": bool(api_key),
        "default_model": DEFAULT_MODEL,
        "features": ["sample_projects", "syntax_validation", "unittest_runner", "security_audit"]
    }


@app.get("/api/models")
async def list_models():
    return {
        "models": [
            {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B Versatile (Recommended)"},
            {"id": "llama-3.1-8b-instant",    "label": "Llama 3.1 8B Instant (Fast)"},
            {"id": "deepseek-r1-distill-llama-70b", "label": "DeepSeek R1 Distill 70B"},
        ]
    }


@app.get("/api/sample-projects")
async def list_sample_projects():
    return {
        "projects": [
            {
                "id": v["id"],
                "name": v["name"],
                "description": v["description"],
                "language": v["language"],
                "file_count": len(v["files"]),
                "suggested_task": v["suggested_task"],
            }
            for v in SAMPLE_PROJECTS.values()
        ]
    }


@app.get("/api/sample-projects/{project_id}")
async def get_sample_project(project_id: str):
    if project_id not in SAMPLE_PROJECTS:
        raise HTTPException(status_code=404, detail="Sample project not found.")
    return SAMPLE_PROJECTS[project_id]


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        if not req.files:
            raise HTTPException(status_code=400, detail="No files provided.")
        analyzer = CodebaseAnalyzer(req.files)
        result = analyzer.analyze()
        result["syntax_validation"] = validate_codebase_syntax(req.files)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/execute-task")
async def execute_task(req: TaskRequest):
    try:
        if not req.files:
            raise HTTPException(status_code=400, detail="No files provided. Please upload a codebase first.")
        if not req.task.strip():
            raise HTTPException(status_code=400, detail="Task description cannot be empty.")

        client = get_groq_client(req.api_key)
        executor = TaskExecutor(
            codebase=req.files,
            analysis=req.analysis,
            client=client,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        result = executor.execute(req.task)
        return JSONResponse(content=result)
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"detail": he.detail})
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})


@app.post("/api/validate-syntax")
async def validate_syntax(req: AnalyzeRequest):
    try:
        if not req.files:
            raise HTTPException(status_code=400, detail="No files provided.")
        val_res = validate_codebase_syntax(req.files)
        return JSONResponse(content=val_res)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/run-tests")
async def run_tests(req: RunTestsRequest):
    try:
        if not req.files:
            raise HTTPException(status_code=400, detail="No files provided.")
        test_res = run_python_tests(req.files)
        return JSONResponse(content=test_res)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/security-audit")
async def security_audit(req: AuditRequest):
    try:
        if not req.files:
            raise HTTPException(status_code=400, detail="No files provided.")

        client = get_groq_client(req.api_key)
        files_str = "\n".join([f"### {fname}\n```\n{content}\n```" for fname, content in req.files.items()])

        prompt = f"""You are a Senior Security Auditor and Code Quality Expert. 
Analyze the codebase below for security risks (OWASP Top 10, SQL injection, unsafe authentication, unhandled exceptions, memory leaks, hardcoded credentials) and quality anti-patterns.

Codebase:
{files_str}

Respond ONLY in JSON format:
```json
{{
  "overall_security_rating": "A | B | C | D | F",
  "issues": [
    {{
      "severity": "HIGH | MEDIUM | LOW",
      "file": "filename.ext",
      "issue": "Short description of vulnerability or anti-pattern",
      "recommendation": "How to fix it"
    }}
  ],
  "summary": "Overall evaluation summary"
}}
```
"""
        messages = [
            {"role": "system", "content": "You are a professional security and code auditor. Respond strictly in valid JSON."},
            {"role": "user", "content": prompt}
        ]

        raw = call_groq(client, messages, req.model, 0.2, 4096)

        try:
            data = json.loads(raw.strip())
        except Exception:
            match = re.search(r"```json\s*([\s\S]+?)\s*```", raw) or re.search(r"\{[\s\S]+\}", raw)
            if match:
                data = json.loads(match.group(1) if "```" in match.group(0) else match.group(0))
            else:
                data = {"overall_security_rating": "B", "issues": [], "summary": raw}

        return JSONResponse(content=data)
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"detail": he.detail})
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    try:
        client = get_groq_client(req.api_key)

        system_content = (
            "You are an expert AI coding assistant. Help developers understand, debug, and improve their code. "
            "Use markdown for formatting. Use code blocks with language tags for all code snippets. "
            "Be clear, concise, and professional."
        )
        if req.files_summary:
            system_content += f"\n\nCodebase context:\n{req.files_summary}"

        messages = [{"role": "system", "content": system_content}] + req.messages

        return StreamingResponse(
            stream_groq(client, messages, req.model, req.temperature, req.max_tokens),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"detail": he.detail})
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})


@app.get("/api/fetch-url")
async def fetch_url(url: str):
    import requests as req_lib
    try:
        r = req_lib.get(url, timeout=10)
        r.raise_for_status()
        filename = url.rstrip("/").split("/")[-1] or "fetched_file.txt"
        return JSONResponse({"filename": filename, "content": r.text})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download")
async def download_zip(req: DownloadRequest):
    try:
        if not req.files:
            raise HTTPException(status_code=400, detail="No files to download.")
        zip_bytes = zip_files_in_memory(req.files)
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=codebase_with_changes.zip"},
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ─── serve frontend ───────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)
