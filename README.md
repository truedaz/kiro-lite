# Kiro‑Lite (Open Source Clone)

A minimal, open-source **spec‑driven, agentic web IDE** inspired by AWS Kiro. It runs locally with a Flask backend and a lightweight front-end using Monaco Editor.

> ⚠️ This is **not** the proprietary AWS Kiro. It’s a clean-room, educational clone that mimics the *workflow* (prompt → spec → tasks → apply) without any AWS IP.

## Features
- Prompt → **Spec** generator (Problem, User Stories, Acceptance Criteria, Design, Tasks)
- Derive **Tasks** from a spec
- **Apply** tasks to scaffold or evolve a small web project
- File tree, Monaco code editor, live **Preview**
- Download your current workspace as a **ZIP**
- Optional: connect to **OpenAI** or **Anthropic** models via env vars; otherwise a deterministic mock is used

## Quick Start

### 1) Create a virtualenv & install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env if you want to use real LLMs (optional)
```

### 2) Run the server
```bash
python app.py
```
The server prints a URL like `http://127.0.0.1:5050`. Open it in your browser.

### 3) Use the IDE
1. Type a prompt and click **Generate Spec**.
2. Click **Derive Tasks**.
3. Click **Apply Next Task** (repeat). The first apply scaffolds a demo app if the workspace is empty.
4. Use the file list to open/edit files with Monaco. Click **Save** to persist.
5. Click **Download Workspace** anytime.

## LLM Setup (Optional)

Edit `server/.env`:
```
OPENAI_API_KEY=sk-...            # or
ANTHROPIC_API_KEY=...

# Optional model overrides:
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
```

If no keys are set, a mock planner/agent produces a minimal spec and scaffolds a counter app.

## Project Layout
```
server/
  app.py
  requirements.txt
  .env.example
  kiro_lite/
    static/
      index.html
      app.js
      styles.css
    workspaces/
      default/         # your files appear here
```

## Commands Recap
```bash
# setup
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# (optionally add your API keys to .env)

# run
python app.py
```

## Notes
- Tested with Python 3.10+.
- The first **Apply Next Task** will create `index.html`, `styles.css`, and `app.js` if the workspace is empty, so you can immediately preview something.
- All workspace edits are plain files on disk; feel free to open the folder in your favorite editor too.

## License
MIT — do whatever you like, no warranty.
