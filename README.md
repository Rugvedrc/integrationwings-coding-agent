# ⚡ AI Coding Agent

> **IntegrationWings Assignment Submission — Shortlisted Candidates 2026**  
> An autonomous AI Coding Agent powered by **Groq (Llama 3.3 70B Versatile)** and **FastAPI / Streamlit** for multi-file codebase understanding, developer task execution, AST syntax validation, unit test execution sandboxing, security auditing, and line-by-line diff reviews.

[![Deployed App](https://img.shields.io/badge/Deployed--App-Live%20on%20Koyeb-brightgreen?style=for-the-badge&logo=fastapi)](https://simple-freida-rsm-b31b17a1.koyeb.app)
[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?style=for-the-badge&logo=github)](https://github.com/Rugvedrc/integrationwings-coding-agent)

---

## 🌟 Key Features & Capabilities

- 🚀 **1-Click Pre-packaged Demo Projects**: Instant evaluation with real-world sample codebases (FastAPI REST API, Node.js Express Auth Service, Python Data Processing Pipeline).
- 📂 **Multi-Language Codebase Analysis**: Supports Python, JavaScript, TypeScript, Java, Go, Rust, C/C++, HTML/CSS, SQL, JSON, YAML, TOML, and Markdown. Automatically parses functions, classes, imports, entry points, and line metrics using AST & regex inspection.
- 🎯 **Automated Developer Task Execution**: Accepts plain-English developer prompts (*"Add input validation"*, *"Write pytest unit tests"*, *"Refactor for performance"*), creates a step-by-step modification plan, and generates complete updated files.
- 🛡️ **AST Syntax Validation Engine**: Automatically verifies Python syntax (`ast.parse`) and JSON/YAML structures across generated files before presenting results to the user.
- 🧪 **Automated Unit Test Sandbox**: Runs `unittest` suites on uploaded or generated Python codebases in an isolated temporary container and displays pass/fail assertions live.
- 🛡️ **AI Security & Quality Audit**: Performs automated code scans for OWASP vulnerabilities, hardcoded secrets, SQL injection risks, and unhandled exception boundaries with letter grade ratings (A, B, C, D, F).
- 🔀 **Interactive Line-by-Line Diff Reviewer**: Visual Side-by-Side and Unified diff inspector with line addition (+), deletion (-) metrics, instant per-file Accept/Reject controls, and an inline **Manual Code Editor**.
- 📦 **One-Click Export**: Download any individual updated file or export the entire project as a `.zip` archive.
- 💬 **Real-Time Streaming Chat Assistant**: Multi-turn developer conversation with real-time SSE token streaming and full codebase context awareness.

---

## 🏗️ System Architecture

```
integrationwings-coding-agent/
├── main.py                  # FastAPI server hosting REST & SSE endpoints
├── app.py                   # Streamlit web application interface
├── agent/
│   ├── codebase_analyzer.py # AST & regex multi-language codebase parser
│   ├── task_executor.py     # LLM task orchestrator & JSON schema engine
│   ├── sample_codebases.py  # Pre-packaged interactive demo codebases
│   ├── validator.py         # AST syntax validator & isolated test sandbox
│   └── utils.py             # Language detection, token estimator, ZIP builder
├── static/
│   ├── index.html           # Professional IDE workspace frontend
│   ├── app.js               # Frontend application logic & SSE streaming
│   └── style.css            # Dark mode glassmorphism IDE stylesheet
├── Dockerfile               # Production container config (Koyeb)
├── requirements.txt         # Production dependencies
├── test_agent.py            # Automated unit test suite
└── README.md                # Technical documentation
```

### Data Flow Pipeline

```
[ User Prompt / Demo Codebase ]
       │
       ▼
[ Codebase Analyzer ] ──► Parses AST, languages, functions, classes, and syntax integrity
       │
       ▼
[ Developer Task Prompt ]
       │
       ▼
[ Task Executor Engine ] ──► Context budgeting (~40k limit) & system prompt contract
       │
       ▼
[ Groq LPU Inference ] ──► (Llama 3.3 70B Versatile / DeepSeek R1 70B)
       │
       ▼
[ JSON Output Contract ] ──► { "plan": "...", "explanation": "...", "changes": { "file": "code" } }
       │
       ▼
[ AST Syntax Check & Test Sandbox ] ──► Validates syntax & runs unit tests
       │
       ▼
[ Diff Inspector & Manual Editor ] ──► Accept / Reject / Edit ──► Export ZIP Archive
```

---

## ⚡ Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Backend API** | [FastAPI](https://fastapi.tiangolo.com) | High-performance async Python web framework supporting SSE streaming |
| **LLM Inference** | [Groq LPU](https://groq.com) | Ultra-fast token generation (~300+ tokens/sec) for real-time code generation |
| **LLM Models** | `llama-3.3-70b-versatile`, `deepseek-r1-distill-llama-70b` | State-of-the-art open models for code understanding, tool calling, and reasoning |
| **Frontend UI** | Vanilla HTML5 / ES6 JavaScript / CSS3 | Modern dark-mode IDE interface without heavy framework overhead |
| **Code Highlighting & Diffs** | Highlight.js & Diff2Html | Professional line-by-line diff viewing and syntax highlighting |
| **Containerization** | Docker | Production deployment on Koyeb |

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
Create a `.env` file in the project root:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 4. Run the application
Run the FastAPI backend server:
```bash
python main.py
```
Open `http://localhost:7860` in your web browser.

*(Alternatively, run the Streamlit interface using `streamlit run app.py`)*

### 5. Run Backend Unit Tests
```bash
python test_agent.py
```

---

## 💡 Approach & Technical Rationale

1. **Strict JSON Schema Contract**: The task engine enforces a mandatory JSON output schema (`{plan, explanation, changes}`). This prevents malformed patch syntax and ensures whole-file integrity.
2. **Context-Aware Budgeting**: Large codebases are scored and filtered by task relevance to fit within optimal context windows.
3. **Automated Verification Pipeline**: Generated code is parsed with Python's native `ast` module to catch any syntax flaws before presentation.
4. **Isolated Test Sandboxing**: Tests are executed inside a temporary workspace directory using Python's `unittest` runner, protecting the primary host system.
5. **Non-Destructive Staging Workflow**: Original files remain unchanged until the user reviews diffs and explicitly accepts proposed changes.
6. **Zero Hardcoded Secrets**: All credentials and API keys are loaded strictly via environment variables or user input. `.env` is strictly git-ignored.

---

## 📄 Submission Details

Submitted for the **IntegrationWings Walk-in Candidate Assignment**:
- **Live Deployed App**: [https://simple-freida-rsm-b31b17a1.koyeb.app](https://simple-freida-rsm-b31b17a1.koyeb.app)
- **GitHub Repository**: [https://github.com/Rugvedrc/integrationwings-coding-agent](https://github.com/Rugvedrc/integrationwings-coding-agent)
