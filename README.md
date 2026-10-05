# 🤖 AI Coding Agent

> **IntegrationWings Assignment Submission — Walk-in Candidates 2026**  
> An autonomous AI Coding Agent powered by **Groq (Llama 3.3 70B)** and **Streamlit** for codebase understanding, natural-language task execution, interactive diff reviews, and ZIP downloads.

[![Deployed App](https://img.shields.io/badge/Deployed--App-Live%20on%20Koyeb-brightgreen?style=for-the-badge&logo=streamlit)](https://simple-freida-rsm-b31b17a1.koyeb.app)
[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?style=for-the-badge&logo=github)](https://github.com/Rugvedrc/integrationwings-coding-agent)

---

## 🌟 Key Features

- 📂 **Multi-Language Codebase Analysis**: Upload files, paste raw code, or fetch from GitHub URLs. Automatically extracts functions, classes, entry points, and line count metrics across Python, JavaScript, TypeScript, Java, Go, and more.
- 🎯 **Automated Developer Task Execution**: Takes high-level developer tasks (*"Add error handling"*, *"Write unit tests"*, *"Refactor functions"*) and generates complete updated files with detailed explanations using **Llama 3.3 70B**.
- 🔀 **Visual Line-by-Line Diff & Review**: Independent side-by-side and unified diff viewer showing additions (+), deletions (-), and line metrics before accepting or rejecting proposed changes.
- 💬 **Real-Time Streaming Chat**: Continuous multi-turn developer Q&A with real-time token streaming (`st.write_stream`) and context awareness.
- 📦 **One-Click Export**: Download any modified single file or export the full updated project as a `.zip` archive.
- 📜 **Task History**: Audit log tracking all executed tasks, models used, modified files, and explanations.

---

## 🏗️ System Architecture

```
integrationwings-coding-agent/
├── app.py                   # Main Streamlit web app & interactive tabs
├── agent/
│   ├── codebase_analyzer.py # Multi-language AST/regex structure parser
│   ├── task_executor.py     # LLM task orchestrator & JSON schema parser
│   └── utils.py             # Language detection, token estimator, ZIP generator
├── assets/
│   └── style.css            # Dark mode UI with glassmorphism & visual tokens
├── .streamlit/
│   └── config.toml          # Streamlit dark theme config
├── Dockerfile               # Container setup for production deployment
├── requirements.txt         # Production Python dependencies
└── README.md                # System documentation
```

### Data Flow Pipeline

```
[ User Input / Files ]
       │
       ▼
[ Codebase Analyzer ] ──► Extracts languages, functions, classes, imports & metrics
       │
       ▼
[ Developer Task Prompt ]
       │
       ▼
[ Task Executor Engine ] ──► Budget-aware prompt builder (~10k token limit)
       │
       ▼
[ Groq LPU Inference ] (Llama 3.3 70B Versatile)
       │
       ▼
[ JSON Output Schema ] ──► { "explanation": "...", "changes": { "file": "code" } }
       │
       ▼
[ Diff Viewer & Review ] ──► Accept / Reject ──► Download Project ZIP
```

---

## ⚡ Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **LLM Inference** | [Groq LPU](https://groq.com) | ~10× faster token generation than standard GPUs for real-time code generation |
| **Primary Model** | `llama-3.3-70b-versatile` | High-reasoning 70B parameter model optimized for code understanding and tool use |
| **Frontend UI** | [Streamlit](https://streamlit.io) | Interactive data & AI web framework with native streaming (`st.write_stream`) |
| **Containerization** | Docker | Production container deployment on Koyeb |

---

## 🚀 Running Locally

### 1. Clone the repository
```bash
git clone https://github.com/Rugvedrc/integrationwings-coding-agent.git
cd integrationwings-coding-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your Groq API key
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 4. Run the Streamlit application
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## 💡 Approach & Technical Rationale

1. **Structured Output Guarantee**: The task engine enforces a strict JSON response contract `{explanation, changes}`. This ensures reliable code extraction without broken diff patches or syntax errors.
2. **Smart Token Budgeting**: Large codebases are dynamically scored and prioritized based on task relevance, fitting file contents into an optimal ~10k token context budget.
3. **Non-Destructive Review Workflow**: Proposed changes are staged in session state. Original files remain untouched until the user reviews the diff and explicitly clicks **Accept**.
4. **Security First**: All API keys are loaded via environment variables (`.env` / platform secrets). `.env` is strictly git-ignored and no secrets or passwords are committed to the repository.

---

## ⚠️ Assumptions & Limitations

- **Context Windows**: Codebases larger than ~40,000 characters are intelligently truncated based on file relevance scoring.
- **Execution Sandboxing**: The agent generates, refactors, and updates code structures; local execution sandboxing was omitted for security and cloud deployment simplicity.
- **File Types**: Optimized for text-based source files (`.py`, `.js`, `.ts`, `.java`, `.go`, `.html`, `.css`, etc.); binary assets are excluded.

---

## 📄 Submission Details

Submitted for the **IntegrationWings Walk-in Interview Assignment**:
- **Live Deployed App**: [https://simple-freida-rsm-b31b17a1.koyeb.app](https://simple-freida-rsm-b31b17a1.koyeb.app)
- **GitHub Repository**: [https://github.com/Rugvedrc/integrationwings-coding-agent](https://github.com/Rugvedrc/integrationwings-coding-agent)
