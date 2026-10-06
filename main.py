"""
AI Coding Agent — FastAPI Backend
IntegrationWings Assignment
"""
import io
import json
import os
import zipfile
from typing import AsyncGenerator

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
from agent.utils import zip_files_in_memory

# ─── setup ──────────────────────────────────────────────────────────────────
load_dotenv()

app = FastAPI(title="AI Coding Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Groq setup ──────────────────────────────────────────────────────────────
FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
]

DEFAULT_MODEL = "openai/gpt-oss-120b"


def get_groq_client(api_key: str | None = None) -> Groq:
    key = api_key or os.getenv("GROQ_API_KEY", "")
    if not key:
        raise HTTPException(status_code=400, detail="No GROQ_API_KEY found. Set it in .env or pass it in the request.")
    return Groq(api_key=key)


def call_groq(client: Groq, messages: list, model: str, temperature: float, max_tokens: int) -> str:
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
            if "404" in str(e) or "model_not_found" in str(e) or "not_found" in str(e).lower():
                continue
            raise e
    raise last_err


async def stream_groq(client: Groq, messages: list, model: str, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
    models = [model] + [m for m in FALLBACK_MODELS if m != model]
    for m in models:
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
            if "404" in str(e) or "model_not_found" in str(e) or "not_found" in str(e).lower():
                continue
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            return
    yield f"data: {json.dumps({'type': 'error', 'content': 'No working model found.'})}\n\n"


# ─── request / response models ───────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    files: dict[str, str]


class TaskRequest(BaseModel):
    files: dict[str, str]
    analysis: dict | None = None
    task: str
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 8192
    api_key: str | None = None


class ChatRequest(BaseModel):
    messages: list[dict]
    files_summary: str = ""
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 4096
    api_key: str | None = None


class DownloadRequest(BaseModel):
    files: dict[str, str]


# ─── routes ──────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def status():
    api_key = os.getenv("GROQ_API_KEY", "")
    return {"ok": True, "api_key_configured": bool(api_key), "default_model": DEFAULT_MODEL}


@app.get("/api/models")
async def list_models():
    return {
        "models": [
            {"id": "openai/gpt-oss-120b", "label": "GPT-OSS 120B (Best)"},
            {"id": "openai/gpt-oss-20b",  "label": "GPT-OSS 20B (Fast)"},
            {"id": "qwen/qwen3.8-27b",    "label": "Qwen3 27B"},
        ]
    }


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.files:
        raise HTTPException(status_code=400, detail="No files provided.")
    analyzer = CodebaseAnalyzer(req.files)
    result = analyzer.analyze()
    return JSONResponse(content=result)


@app.post("/api/execute-task")
async def execute_task(req: TaskRequest):
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


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
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
    if not req.files:
        raise HTTPException(status_code=400, detail="No files to download.")
    zip_bytes = zip_files_in_memory(req.files)
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=codebase_with_changes.zip"},
    )


# ─── serve frontend ───────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)
