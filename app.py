"""
AI Coding Agent — Powered by Groq + Streamlit
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
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/rugved/integrationwings-coding-agent",
        "Report a bug": "https://github.com/rugved/integrationwings-coding-agent/issues",
        "About": "# AI Coding Agent\nBuilt with Groq + Streamlit for the IntegrationWings assignment.",
    },
)

# ─── CSS injection ────────────────────────────────────────────────────────────
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
    "selected_model": "openai/gpt-oss-120b",
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


FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "allam-2-7b"]


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
    st.markdown('<div class="sidebar-header"><span class="robot-icon">🤖</span><h1>AI Coding Agent</h1></div>', unsafe_allow_html=True)
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
        "💡 Mixtral 8x7B": "mixtral-8x7b-32768",
    }
    selected_label = st.selectbox("Model", list(MODELS.keys()), index=0)
    st.session_state.selected_model = MODELS[selected_label]

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.temperature = st.slider("🌡️ Temp", 0.0, 1.0, 0.3, 0.05)
    with col2:
        st.session_state.max_tokens = st.select_slider(
            "Max Tokens", options=[1024, 2048, 4096, 8192, 16384, 32768], value=8192
        )

    st.session_state.stream_enabled = st.toggle("⚡ Stream Responses", value=True)

    st.divider()

    # ── codebase upload ───────────────────────────────────────────────────
    st.markdown("### 📁 Codebase Upload")
    upload_mode = st.radio("Input Method", ["📂 Upload Files", "✍️ Paste Code", "🔗 GitHub URL"], label_visibility="collapsed")

    if upload_mode == "📂 Upload Files":
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
        st.markdown("### 📊 Codebase Stats")
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
st.markdown('<div class="main-header"><h1>🤖 AI Coding Agent</h1><p class="subtitle">Understand · Propose · Transform your codebase with AI</p></div>', unsafe_allow_html=True)

tab_chat, tab_explorer, tab_diff, tab_history = st.tabs(
    ["💬 Chat & Task", "📂 Code Explorer", "🔀 Diff Viewer", "📜 Task History"]
)

# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1 — CHAT & TASK
# ─────────────────────────────────────────────────────────────────────────────
with tab_chat:
    # ── analyze codebase button ───────────────────────────────────────────
    if st.session_state.codebase and st.session_state.analysis is None and client_ready:
        with st.spinner("🔍 Analyzing codebase structure…"):
            analyzer = CodebaseAnalyzer(st.session_state.codebase)
            st.session_state.analysis = analyzer.analyze()
        st.success("✅ Codebase analyzed! You can now ask the agent to perform tasks.")

    # ── info banner ───────────────────────────────────────────────────────
    if not st.session_state.codebase:
        st.info("👈 Upload files in the sidebar to get started, or chat directly with the agent.")

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

    # ── task input ────────────────────────────────────────────────────────
    st.markdown("#### 🎯 Developer Task")
    task_col, btn_col = st.columns([5, 1])

    QUICK_TASKS = [
        "Custom task…",
        "Add comprehensive docstrings to all functions",
        "Refactor to follow PEP 8 / ESLint best practices",
        "Add unit tests for all public functions",
        "Fix any bugs or anti-patterns you find",
        "Add type hints / TypeScript types",
        "Optimize performance bottlenecks",
        "Add error handling and logging",
        "Convert to async/await pattern",
        "Generate a README.md for this project",
    ]
    quick_sel = st.selectbox("Quick Tasks", QUICK_TASKS, label_visibility="collapsed")

    with task_col:
        task_input = st.text_area(
            "Describe the task",
            value="" if quick_sel == "Custom task…" else quick_sel,
            height=80,
            placeholder="e.g. Add error handling to all API calls, refactor the auth module, add unit tests…",
            key="task_input_box",
            label_visibility="collapsed",
        )
    with btn_col:
        execute_btn = st.button("🚀 Execute", use_container_width=True, type="primary", disabled=not client_ready)

    # ── execute task ──────────────────────────────────────────────────────
    if execute_btn and task_input.strip():
        if not client_ready:
            st.error("❌ No Groq API key configured.")
        else:
            executor = TaskExecutor(
                codebase=st.session_state.codebase,
                analysis=st.session_state.analysis,
                model=st.session_state.selected_model,
                temperature=st.session_state.temperature,
                max_tokens=st.session_state.max_tokens,
                stream_fn=stream_response,
                full_fn=full_response,
            )

            with st.spinner("🤖 Agent is working…"):
                result = executor.execute(task_input.strip())

            if result.get("proposed_changes"):
                st.session_state.proposed_changes.update(result["proposed_changes"])
                # Store in history
                st.session_state.task_history.append({
                    "task": task_input.strip(),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "changes": list(result["proposed_changes"].keys()),
                    "explanation": result.get("explanation", ""),
                    "model": st.session_state.selected_model,
                })

            # Add to chat
            st.session_state.messages.append({"role": "user", "content": f"🎯 Task: {task_input.strip()}"})
            st.session_state.messages.append({
                "role": "assistant",
                "content": result.get("explanation", "Task complete."),
                "changes": result.get("proposed_changes", {}),
            })
            st.rerun()

    st.divider()

    # ── chat messages ─────────────────────────────────────────────────────
    st.markdown("#### 💬 Conversation")

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("changes"):
                    with st.expander(f"📝 {len(msg['changes'])} file(s) modified — view changes"):
                        for fname, new_code in msg["changes"].items():
                            st.markdown(f"**`{fname}`**")
                            lang = get_language_from_ext(fname)
                            st.code(new_code, language=lang, line_numbers=True)

    # ── chat input ────────────────────────────────────────────────────────
    if prompt := st.chat_input("Ask the agent anything about your code…", disabled=not client_ready):
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Build system prompt
        system_parts = [
            "You are an expert AI coding assistant. You help developers understand, debug, and improve codebases.",
            "When asked to modify code, always explain your changes clearly.",
            "Use markdown formatting. Use code blocks with language tags.",
        ]
        if st.session_state.analysis:
            system_parts.append(f"\nCodebase context:\n{json.dumps(st.session_state.analysis, indent=2)}")
        if st.session_state.codebase:
            # Add file listing (not full content to save tokens)
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
    st.markdown("### 📂 Code Explorer")

    if not st.session_state.codebase:
        st.info("No codebase loaded. Upload files via the sidebar.")
    else:
        view_mode = st.radio("View", ["Original", "Proposed Changes"], horizontal=True, key="explorer_view")
        source = (
            st.session_state.codebase
            if view_mode == "Original"
            else {**st.session_state.codebase, **st.session_state.proposed_changes}
        )

        selected_file = st.selectbox(
            "Select file",
            list(source.keys()),
            format_func=lambda x: (
                f"✏️ {x}" if x in st.session_state.proposed_changes else f"📄 {x}"
            ),
        )

        if selected_file:
            file_content = source[selected_file]
            lang = get_language_from_ext(selected_file)

            col_meta, col_dl = st.columns([4, 1])
            with col_meta:
                lines = file_content.count("\n") + 1
                chars = len(file_content)
                st.caption(f"**{selected_file}** · {lines} lines · {chars:,} chars · Language: `{lang}`")
            with col_dl:
                st.download_button(
                    "⬇️ Download",
                    file_content,
                    file_name=selected_file,
                    mime="text/plain",
                    use_container_width=True,
                )

            st.code(file_content, language=lang, line_numbers=True)

        # ── download all as ZIP ───────────────────────────────────────────
        if st.session_state.proposed_changes:
            all_files = {**st.session_state.codebase, **st.session_state.proposed_changes}
            zip_buf = zip_files_in_memory(all_files)
            st.download_button(
                "📦 Download All (with changes) as ZIP",
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
        st.info("No proposed changes yet. Execute a task in the Chat tab to see diffs here.")
    else:
        changed_files = list(st.session_state.proposed_changes.keys())
        st.success(f"✅ {len(changed_files)} file(s) have proposed changes.")

        diff_file = st.selectbox("Select file to diff", changed_files, key="diff_file_select")

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
                    lineterm="",
                ))
                if diff_lines:
                    diff_text = "".join(diff_lines)
                    st.code(diff_text, language="diff", line_numbers=True)
                else:
                    st.info("No changes detected.")

            else:  # side-by-side
                orig_lines = original.splitlines()
                new_lines = proposed.splitlines()
                col_orig, col_new = st.columns(2)
                with col_orig:
                    st.markdown(f"**Before: `{diff_file}`**")
                    lang = get_language_from_ext(diff_file)
                    st.code(original, language=lang, line_numbers=True)
                with col_new:
                    st.markdown(f"**After: `{diff_file}`**")
                    st.code(proposed, language=lang, line_numbers=True)

            # stats
            added = sum(1 for l in difflib.unified_diff(original.splitlines(), proposed.splitlines()) if l.startswith("+") and not l.startswith("+++"))
            removed = sum(1 for l in difflib.unified_diff(original.splitlines(), proposed.splitlines()) if l.startswith("-") and not l.startswith("---"))
            c1, c2, c3 = st.columns(3)
            c1.metric("Lines Added", f"+{added}", delta=added, delta_color="normal")
            c2.metric("Lines Removed", f"-{removed}", delta=-removed, delta_color="inverse")
            c3.metric("Net Change", added - removed)

            # accept / reject buttons
            st.divider()
            col_accept, col_reject = st.columns(2)
            with col_accept:
                if st.button(f"✅ Accept changes to `{diff_file}`", use_container_width=True, type="primary"):
                    st.session_state.codebase[diff_file] = proposed
                    st.session_state.original_files[diff_file] = proposed
                    del st.session_state.proposed_changes[diff_file]
                    st.success(f"✅ Changes to `{diff_file}` accepted!")
                    st.rerun()
            with col_reject:
                if st.button(f"❌ Reject changes to `{diff_file}`", use_container_width=True):
                    del st.session_state.proposed_changes[diff_file]
                    st.warning(f"❌ Changes to `{diff_file}` rejected.")
                    st.rerun()

        if st.button("✅ Accept ALL changes", use_container_width=True, type="primary"):
            for fname, content in st.session_state.proposed_changes.items():
                st.session_state.codebase[fname] = content
                st.session_state.original_files[fname] = content
            st.session_state.proposed_changes = {}
            st.success("✅ All changes accepted!")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 4 — TASK HISTORY
# ─────────────────────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📜 Task History")

    if not st.session_state.task_history:
        st.info("No tasks executed yet.")
    else:
        for i, task in enumerate(reversed(st.session_state.task_history)):
            with st.expander(f"**#{len(st.session_state.task_history) - i}** · {task['task'][:60]}… · `{task['timestamp']}`"):
                st.markdown(f"**Task:** {task['task']}")
                st.markdown(f"**Model:** `{task['model']}`")
                st.markdown(f"**Files modified:** {', '.join(f'`{f}`' for f in task['changes']) or 'None'}")
                if task.get("explanation"):
                    st.markdown("**Explanation:**")
                    st.markdown(task["explanation"])

        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.task_history = []
            st.rerun()
