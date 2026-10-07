"""
AI Coding Agent — Streamlit Interface
IntegrationWings Assignment
"""

import streamlit as st
import os
import json
import zipfile
import io
import difflib
import time
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from groq import Groq

# ─── local modules ───────────────────────────────────────────────────────────
from agent.codebase_analyzer import CodebaseAnalyzer
from agent.task_executor import TaskExecutor
from agent.sample_codebases import SAMPLE_PROJECTS
from agent.validator import validate_codebase_syntax, run_python_tests
from agent.utils import (
    highlight_code,
    render_diff,
    get_language_from_ext,
    zip_files_in_memory,
    count_tokens_approx,
)

# ─── env & page config ───────────────────────────────────────────────────────
load_dotenv()

st.set_page_config(
    page_title="AI Coding Agent | IntegrationWings",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/Rugvedrc/integrationwings-coding-agent",
        "Report a bug": "https://github.com/Rugvedrc/integrationwings-coding-agent/issues",
        "About": "# AI Coding Agent\nBuilt with Groq + FastAPI / Streamlit for the IntegrationWings assignment.",
    },
)

# ─── CSS injection ────────────────────────────────────────────────────────────
if os.path.exists("assets/style.css"):
    with open("assets/style.css", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── session state defaults ──────────────────────────────────────────────────
DEFAULTS = {
    "messages": [],
    "codebase": {},          # {filename: content}
    "analysis": None,        # CodebaseAnalyzer result
    "proposed_changes": {},  # {filename: new_content}
    "original_files": {},    # {filename: original_content}
    "task_history": [],
    "active_tab": "chat",
    "groq_client": None,
    "selected_model": "llama-3.3-70b-versatile",
    "stream_enabled": True,
    "show_diff": False,
    "temperature": 0.3,
    "max_tokens": 8192,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Groq client factory ─────────────────────────────────────────────────────
@st.cache_resource
def get_groq_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


def init_client():
    api_key = os.getenv("GROQ_API_KEY") or st.session_state.get("manual_api_key", "")
    if api_key:
        st.session_state.groq_client = get_groq_client(api_key)
        return True
    return False


FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "deepseek-r1-distill-llama-70b",
]


# ─── streaming wrapper ───────────────────────────────────────────────────────
def stream_response(messages: list, model: str, temperature: float, max_tokens: int) -> Generator:
    client: Groq = st.session_state.groq_client
    models_to_try = [model] + [m for m in FALLBACK_MODELS if m != model]
    
    for m in models_to_try:
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
                    yield delta
            return
        except Exception as e:
            if "404" in str(e) or "model_not_found" in str(e):
                continue
            raise e


def full_response(messages: list, model: str, temperature: float, max_tokens: int) -> str:
    client: Groq = st.session_state.groq_client
    models_to_try = [model] + [m for m in FALLBACK_MODELS if m != model]
    
    last_error = None
    for m in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            return completion.choices[0].message.content
        except Exception as e:
            last_error = e
            if "404" in str(e) or "model_not_found" in str(e):
                continue
            raise e
    raise last_error


# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('### ⚡ AI Coding Agent', unsafe_allow_html=True)
    st.caption("Powered by Groq · IntegrationWings Assignment")
    st.divider()

    # ── API key ───────────────────────────────────────────────────────────
    with st.expander("🔑 API Configuration", expanded=not bool(os.getenv("GROQ_API_KEY"))):
        env_key = os.getenv("GROQ_API_KEY", "")
        if env_key:
            st.success("✅ API key loaded from .env", icon="✅")
        else:
            manual_key = st.text_input("Enter Groq API Key", type="password", key="manual_api_key_input",
                                       placeholder="gsk_...")
            if manual_key:
                st.session_state["manual_api_key"] = manual_key

    client_ready = init_client()
    if not client_ready:
        st.warning("⚠️ No API key found. Add GROQ_API_KEY to .env or enter it above.")

    st.divider()

    # ── model selector ────────────────────────────────────────────────────
    st.markdown("### ⚙️ Model Settings")
    MODELS = {
        "🦙 Llama 3.3 70B Versatile (Recommended)": "llama-3.3-70b-versatile",
        "⚡ Llama 3.1 8B Instant": "llama-3.1-8b-instant",
        "💡 Mixtral 8x7B (32k Context)": "mixtral-8x7b-32768",
        "🔍 DeepSeek R1 Distill 70B": "deepseek-r1-distill-llama-70b",
    }
    selected_label = st.selectbox("Model", list(MODELS.keys()), index=0)
    st.session_state.selected_model = MODELS[selected_label]

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.temperature = st.slider("🌡️ Temp", 0.0, 1.0, 0.3, 0.05)
    with col2:
        st.session_state.max_tokens = st.select_slider(
            "Max Tokens", options=[1024, 2048, 4096, 8192, 16384], value=8192
        )

    st.session_state.stream_enabled = st.toggle("⚡ Stream Responses", value=True)

    st.divider()

    # ── codebase upload & demo projects ────────────────────────────────────
    st.markdown("### 📁 Codebase Input")
    upload_mode = st.radio("Input Method", ["🚀 Demo Projects", "📂 Upload Files", "✍️ Paste Code", "🔗 GitHub URL"], label_visibility="collapsed")

    if upload_mode == "🚀 Demo Projects":
        demo_choice = st.selectbox("Select Sample Project", list(SAMPLE_PROJECTS.keys()), format_func=lambda x: SAMPLE_PROJECTS[x]["name"])
        if st.button("🚀 Load Sample Project", use_container_width=True):
            proj = SAMPLE_PROJECTS[demo_choice]
            st.session_state.codebase = dict(proj["files"])
            st.session_state.original_files = dict(proj["files"])
            st.session_state.analysis = None
            st.session_state.proposed_changes = {}
            st.success(f"✅ Loaded: {proj['name']}")
            st.rerun()

    elif upload_mode == "📂 Upload Files":
        uploaded_files = st.file_uploader(
            "Upload source files",
            accept_multiple_files=True,
            type=["py", "js", "ts", "jsx", "tsx", "java", "cpp", "c", "cs", "go",
                  "rs", "rb", "php", "html", "css", "json", "yaml", "yml", "md",
                  "txt", "toml", "sh", "sql"],
        )
        if uploaded_files:
            new_codebase = {}
            for f in uploaded_files:
                try:
                    new_codebase[f.name] = f.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
            if new_codebase != st.session_state.codebase:
                st.session_state.codebase = new_codebase
                st.session_state.original_files = dict(new_codebase)
                st.session_state.analysis = None
                st.session_state.proposed_changes = {}
                st.success(f"✅ {len(new_codebase)} file(s) loaded!")

    elif upload_mode == "✍️ Paste Code":
        paste_name = st.text_input("Filename", placeholder="main.py")
        paste_code = st.text_area("Paste your code here", height=200, placeholder="# paste code...")
        if st.button("➕ Add to Codebase") and paste_name and paste_code:
            st.session_state.codebase[paste_name] = paste_code
            st.session_state.original_files[paste_name] = paste_code
            st.session_state.analysis = None
            st.success(f"✅ Added: {paste_name}")

    elif upload_mode == "🔗 GitHub URL":
        gh_url = st.text_input("GitHub raw file URL", placeholder="https://raw.githubusercontent.com/...")
        if st.button("⬇️ Fetch File") and gh_url:
            import requests
            try:
                r = requests.get(gh_url, timeout=10)
                r.raise_for_status()
                fname = gh_url.split("/")[-1]
                st.session_state.codebase[fname] = r.text
                st.session_state.original_files[fname] = r.text
                st.session_state.analysis = None
                st.success(f"✅ Fetched: {fname}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.divider()

    # ── codebase stats ────────────────────────────────────────────────────
    if st.session_state.codebase:
        total_lines = sum(c.count("\n") for c in st.session_state.codebase.values())
        total_chars = sum(len(c) for c in st.session_state.codebase.values())
        st.markdown("### 📊 Codebase Metrics")
        c1, c2 = st.columns(2)
        c1.metric("Files", len(st.session_state.codebase))
        c2.metric("Lines", f"{total_lines:,}")
        c1.metric("Tokens ~", f"{count_tokens_approx(total_chars):,}")
        c2.metric("Size", f"{total_chars / 1024:.1f} KB")

        if st.button("🗑️ Clear Codebase", use_container_width=True):
            for k in ["codebase", "original_files", "analysis", "proposed_changes"]:
                st.session_state[k] = {} if k != "analysis" else None
            st.rerun()

    st.divider()
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.task_history = []
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN AREA — TABS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('# ⚡ AI Coding Agent', unsafe_allow_html=True)
st.caption("Understand · Propose · Transform your codebase with AI")

tab_chat, tab_explorer, tab_diff, tab_audit, tab_tests, tab_history = st.tabs(
    ["🎯 Chat & Task", "📂 Code Explorer", "🔀 Diff Viewer", "🛡️ Security Audit", "🧪 Test Sandbox", "📜 Task History"]
)

# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1 — CHAT & TASK
# ─────────────────────────────────────────────────────────────────────────────
with tab_chat:
    if st.session_state.codebase and st.session_state.analysis is None and client_ready:
        with st.spinner("🔍 Analyzing codebase structure & syntax…"):
            analyzer = CodebaseAnalyzer(st.session_state.codebase)
            st.session_state.analysis = analyzer.analyze()
        st.success("✅ Codebase analyzed! You can now execute tasks.")

    if not st.session_state.codebase:
        st.info("👈 Upload files or select a Demo Project in the sidebar to get started.")

    if st.session_state.analysis:
        with st.expander("🔍 Codebase Analysis Summary", expanded=False):
            analysis = st.session_state.analysis
            cols = st.columns(4)
            cols[0].metric("Total Files", analysis.get("file_count", 0))
            cols[1].metric("Total Lines", f"{analysis.get('total_lines', 0):,}")
            cols[2].metric("Languages", len(analysis.get("languages", {})))
            cols[3].metric("Functions", analysis.get("function_count", 0))

            if analysis.get("languages"):
                st.markdown("**Language Breakdown:**")
                lang_items = sorted(analysis["languages"].items(), key=lambda x: x[1], reverse=True)
                for lang, count in lang_items[:8]:
                    pct = (count / analysis.get("file_count", 1)) * 100
                    st.markdown(f"  `{lang}` — {count} file(s) ({pct:.0f}%)")

            if analysis.get("summary"):
                st.markdown("**Structure Summary:**")
                st.markdown(analysis["summary"])

    st.markdown("#### 🎯 Developer Task")
    task_col, btn_col = st.columns([5, 1])

    QUICK_TASKS = [
        "Custom task…",
        "Add comprehensive docstrings and error handling",
        "Add unit tests for all public functions and APIs",
        "Refactor functions to follow clean code best practices",
        "Fix potential bugs, anti-patterns, or security risks",
        "Generate a technical README.md for this project",
    ]
    quick_sel = st.selectbox("Task Presets", QUICK_TASKS, label_visibility="collapsed")

    with task_col:
        task_input = st.text_area(
            "Describe the task",
            value="" if quick_sel == "Custom task…" else quick_sel,
            height=80,
            placeholder="e.g. Add input validation to API endpoints and write unit tests…",
            key="task_input_box",
            label_visibility="collapsed",
        )
    with btn_col:
        execute_btn = st.button("🚀 Execute", use_container_width=True, type="primary", disabled=not client_ready)

    if execute_btn and task_input.strip():
        if not client_ready:
            st.error("❌ No Groq API key configured.")
        else:
            client = st.session_state.groq_client
            executor = TaskExecutor(
                codebase=st.session_state.codebase,
                analysis=st.session_state.analysis,
                client=client,
                model=st.session_state.selected_model,
                temperature=st.session_state.temperature,
                max_tokens=st.session_state.max_tokens,
            )

            with st.spinner("🤖 Agent is working & validating syntax…"):
                result = executor.execute(task_input.strip())

            if result.get("proposed_changes"):
                st.session_state.proposed_changes.update(result["proposed_changes"])
                st.session_state.task_history.append({
                    "task": task_input.strip(),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "changes": list(result["proposed_changes"].keys()),
                    "explanation": result.get("explanation", ""),
                    "model": st.session_state.selected_model,
                })

            st.session_state.messages.append({"role": "user", "content": f"🎯 Task: {task_input.strip()}"})
            st.session_state.messages.append({
                "role": "assistant",
                "content": result.get("explanation", "Task complete."),
                "changes": result.get("proposed_changes", {}),
            })
            st.rerun()

    st.divider()

    st.markdown("#### 💬 Conversation & Q&A")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("changes"):
                with st.expander(f"📝 {len(msg['changes'])} file(s) modified — view proposed changes"):
                    for fname, new_code in msg["changes"].items():
                        st.markdown(f"**`{fname}`**")
                        lang = get_language_from_ext(fname)
                        st.code(new_code, language=lang, line_numbers=True)

    if prompt := st.chat_input("Ask anything about your code…", disabled=not client_ready):
        st.session_state.messages.append({"role": "user", "content": prompt})

        system_parts = [
            "You are an expert AI coding assistant. You help developers understand, debug, and improve codebases.",
            "Use markdown formatting. Use code blocks with language tags.",
        ]
        if st.session_state.analysis:
            system_parts.append(f"\nCodebase context:\n{json.dumps(st.session_state.analysis, indent=2)}")
        if st.session_state.codebase:
            files_list = "\n".join(f"- {k} ({v.count(chr(10))} lines)" for k, v in st.session_state.codebase.items())
            system_parts.append(f"\nFiles in codebase:\n{files_list}")

        msgs = [{"role": "system", "content": "\n".join(system_parts)}]
        msgs += [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
        msgs.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            if st.session_state.stream_enabled:
                response_text = st.write_stream(
                    stream_response(msgs, st.session_state.selected_model,
                                    st.session_state.temperature, st.session_state.max_tokens)
                )
            else:
                with st.spinner("Thinking…"):
                    response_text = full_response(msgs, st.session_state.selected_model,
                                                  st.session_state.temperature, st.session_state.max_tokens)
                st.markdown(response_text)

        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2 — CODE EXPLORER
# ─────────────────────────────────────────────────────────────────────────────
with tab_explorer:
    st.markdown("### 📂 Codebase Explorer")

    if not st.session_state.codebase:
        st.info("No codebase loaded.")
    else:
        view_mode = st.radio("View Mode", ["Original Codebase", "With Proposed Changes"], horizontal=True)
        source = (
            st.session_state.codebase
            if view_mode == "Original Codebase"
            else {**st.session_state.codebase, **st.session_state.proposed_changes}
        )

        selected_file = st.selectbox(
            "Select file to view",
            list(source.keys()),
            format_func=lambda x: f"✏️ {x}" if x in st.session_state.proposed_changes else f"📄 {x}",
        )

        if selected_file:
            file_content = source[selected_file]
            lang = get_language_from_ext(selected_file)

            col_meta, col_dl = st.columns([4, 1])
            with col_meta:
                st.caption(f"**{selected_file}** · {file_content.count(chr(10))+1} lines · {len(file_content):,} chars")
            with col_dl:
                st.download_button(
                    "⬇️ Download File",
                    file_content,
                    file_name=selected_file,
                    mime="text/plain",
                    use_container_width=True,
                )

            st.code(file_content, language=lang, line_numbers=True)

        if st.session_state.proposed_changes:
            all_files = {**st.session_state.codebase, **st.session_state.proposed_changes}
            zip_buf = zip_files_in_memory(all_files)
            st.download_button(
                "📦 Export Full Codebase as ZIP",
                data=zip_buf,
                file_name="codebase_with_changes.zip",
                mime="application/zip",
                use_container_width=True,
                type="primary",
            )


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3 — DIFF VIEWER
# ─────────────────────────────────────────────────────────────────────────────
with tab_diff:
    st.markdown("### 🔀 Diff Viewer")

    if not st.session_state.proposed_changes:
        st.info("No proposed changes yet. Execute a task to see diffs.")
    else:
        changed_files = list(st.session_state.proposed_changes.keys())
        st.success(f"✅ {len(changed_files)} file(s) have proposed changes.")

        diff_file = st.selectbox("Select file to diff", changed_files)

        if diff_file:
            original = st.session_state.original_files.get(diff_file, "")
            proposed = st.session_state.proposed_changes.get(diff_file, "")

            diff_format = st.radio("Diff format", ["Unified", "Side-by-side"], horizontal=True)

            if diff_format == "Unified":
                diff_lines = list(difflib.unified_diff(
                    original.splitlines(keepends=True),
                    proposed.splitlines(keepends=True),
                    fromfile=f"a/{diff_file}",
                    tofile=f"b/{diff_file}",
                ))
                st.code("".join(diff_lines), language="diff", line_numbers=True)
            else:
                col_orig, col_new = st.columns(2)
                lang = get_language_from_ext(diff_file)
                with col_orig:
                    st.markdown(f"**Before (`a/{diff_file}`)**")
                    st.code(original, language=lang, line_numbers=True)
                with col_new:
                    st.markdown(f"**After (`b/{diff_file}`)**")
                    st.code(proposed, language=lang, line_numbers=True)

            col_acc, col_rej = st.columns(2)
            with col_acc:
                if st.button(f"✅ Accept `{diff_file}`", use_container_width=True, type="primary"):
                    st.session_state.codebase[diff_file] = proposed
                    st.session_state.original_files[diff_file] = proposed
                    del st.session_state.proposed_changes[diff_file]
                    st.success(f"Accepted `{diff_file}`")
                    st.rerun()
            with col_rej:
                if st.button(f"❌ Reject `{diff_file}`", use_container_width=True):
                    del st.session_state.proposed_changes[diff_file]
                    st.warning(f"Rejected `{diff_file}`")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 4 — SECURITY AUDIT
# ─────────────────────────────────────────────────────────────────────────────
with tab_audit:
    st.markdown("### 🛡️ Security & Code Quality Audit")
    if not st.session_state.codebase:
        st.info("No codebase loaded.")
    else:
        if st.button("🛡️ Run Security Scan", type="primary"):
            client = st.session_state.groq_client
            files_str = "\n".join([f"### {fname}\n```\n{content}\n```" for fname, content in st.session_state.codebase.items()])
            prompt = f"Analyze for security risks and code quality:\n{files_str}"
            with st.spinner("Scanning codebase..."):
                raw = full_response([{"role": "system", "content": "Security auditor"}, {"role": "user", "content": prompt}],
                                    st.session_state.selected_model, 0.2, 4096)
                st.markdown(raw)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 5 — TEST SANDBOX
# ─────────────────────────────────────────────────────────────────────────────
with tab_tests:
    st.markdown("### 🧪 Unit Test Sandbox")
    active_files = {**st.session_state.codebase, **st.session_state.proposed_changes}
    if not active_files:
        st.info("No codebase loaded.")
    else:
        if st.button("🧪 Execute Unit Tests", type="primary"):
            with st.spinner("Running python unit tests..."):
                res = run_python_tests(active_files)
                if res.get("success"):
                    st.success(res.get("summary"))
                else:
                    st.error(res.get("summary"))
                st.code(res.get("stdout", "") + "\n" + res.get("stderr", ""), language="text")


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 6 — TASK HISTORY
# ─────────────────────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📜 Task Execution Log")
    if not st.session_state.task_history:
        st.info("No tasks executed yet.")
    else:
        for idx, item in enumerate(reversed(st.session_state.task_history)):
            with st.expander(f"Task #{len(st.session_state.task_history) - idx} — {item['task'][:50]}…"):
                st.markdown(f"**Task:** {item['task']}")
                st.markdown(f"**Timestamp:** `{item['timestamp']}` | **Model:** `{item['model']}`")
                st.markdown(f"**Modified Files:** {', '.join(item['changes'])}")
                st.markdown(item["explanation"])
