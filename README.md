# 🤖 IntegrationWings AI Coding Agent

> **AI Coding Assignment — IntegrationWings Walk-in Interview 2026**  
> Built with **Groq (Llama 3.3 70B)** + **Streamlit** · Submitted by Rugved

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://YOUR_APP.streamlit.app)

---

## 🚀 What It Does

An AI-powered coding agent that can:

| Feature | Description |
|---------|-------------|
| 📂 **Codebase Understanding** | Upload files, paste code, or fetch from GitHub URLs; auto-analyzes language, functions, classes, and structure |
| 🎯 **Task Execution** | Accepts natural-language developer tasks and proposes precise code changes |
| 🔀 **Diff Viewer** | Side-by-side and unified diff of every proposed change |
| ✅ **Accept / Reject** | Accept or reject each file change independently |
| 💬 **Chat Interface** | Streaming, multi-turn conversation with full codebase context |
| 📦 **Export** | Download any file or the entire modified codebase as a ZIP |
| 📜 **Task History** | Full log of every executed task and its model/output |

---

## 🏗️ Architecture

```
integrationwings-coding-agent/
├── app.py                   # Main Streamlit UI
├── agent/
│   ├── codebase_analyzer.py # Multi-language code parser (functions, classes, imports)
│   ├── task_executor.py     # Orchestrates LLM to perform tasks + JSON output parser
│   └── utils.py             # Helpers (language detection, ZIP, diff, token count)
├── assets/
│   └── style.css            # Premium dark-mode UI (glassmorphism + gradients)
├── .streamlit/
│   └── config.toml          # Streamlit dark theme config
├── .env                     # Local secrets (GROQ_API_KEY) — not committed
├── requirements.txt
└── README.md
```

### Flow Diagram

```
User uploads files
       │
       ▼
CodebaseAnalyzer ──► extracts languages, functions, classes, summary
       │
       ▼
User enters task ──► TaskExecutor
       │                   │
       │             Builds prompt with
       │             codebase context
       │                   │
       │                   ▼
       │          Groq LLM (Llama 3.3 70B)
       │                   │
       │          Returns JSON: {explanation, changes}
       │                   │
       ▼                   ▼
  Chat + Diff Viewer ◄─── Proposed changes stored in session
       │
  Accept / Reject
       │
  Export as ZIP
```

---

## ⚡ Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM Inference** | [Groq](https://groq.com) — LPU-powered ultra-fast inference |
| **Model** | `llama-3.3-70b-versatile` (default), with Llama 4 / Mixtral options |
| **UI** | [Streamlit](https://streamlit.io) with streaming (`st.write_stream`) |
| **Code Analysis** | Custom regex-based multi-language parser (Python/JS/TS/Java/Go/…) |
| **Deployment** | [Streamlit Community Cloud](https://share.streamlit.io) |

---

## 🛠️ Running Locally

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/integrationwings-coding-agent.git
cd integrationwings-coding-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your Groq API key
Create a `.env` file:
```env
GROQ_API_KEY=gsk_your_key_here
```
Get your free key at [console.groq.com](https://console.groq.com).

### 4. Run the app
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## ☁️ Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **Create app** → select your repo → set main file to `app.py`
4. Under **Advanced settings → Secrets**, add:
   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   ```
5. Click **Deploy** — done!

---

## 💡 Approach & Design Decisions

### Why Groq?
Groq's LPU inference provides **~10× faster** token generation than typical GPU inference. For a coding agent where users expect near-real-time code generation, this is transformative.

### Structured JSON Output
The agent always returns a strict JSON schema `{explanation, changes}`. This ensures:
- Reliable parsing even when models add extra prose
- Every file gets its **complete** new content (no partial diffs that break merging)
- Clear explanation of every change for transparency

### Smart Context Management
Large codebases exceed LLM context limits. The executor scores files by relevance to the task and includes as many as will fit (40k char budget ≈ 10k tokens), truncating gracefully.

### Session-based Diff / Accept / Reject
Proposed changes never overwrite the original until the user explicitly accepts them. This mirrors real-world code review workflows.

---

## ⚠️ Limitations & Assumptions

- **Context window**: Very large codebases (>300 files) may require selecting specific files
- **Binary files**: Only text-based source files are supported
- **Execution**: The agent proposes changes but does not execute/test code (sandboxing is out of scope for this assignment)
- **API rate limits**: Groq free tier has per-minute token limits; complex tasks may need retries
- **Language support**: Best results for Python, JavaScript, TypeScript, Java, Go; other languages work but with less structure extraction

---

## 📄 License

MIT — built for the IntegrationWings coding assignment.
