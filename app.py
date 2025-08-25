
import os, json, re, pathlib, uuid, shutil
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
from pydantic import BaseModel
from dotenv import load_dotenv

# Optional LLM clients
try:
    import openai
except Exception:
    openai = None

try:
    import anthropic
except Exception:
    anthropic = None

load_dotenv()

PORT = int(os.environ.get("PORT", "5050"))
WORKSPACE = pathlib.Path(os.environ.get("WORKSPACE", "./kiro_lite/workspaces/default")).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder="kiro_lite/static", static_url_path="/static")
CORS(app)

# -------- Utilities --------
def safe_join(base: pathlib.Path, *parts: str) -> pathlib.Path:
    p = (base.joinpath(*parts)).resolve()
    if not str(p).startswith(str(base)):
        raise ValueError("Unsafe path")
    return p

def list_files(base_dir: pathlib.Path):
    files = []
    for root, dirs, fs in os.walk(base_dir):
        for f in fs:
            rel = pathlib.Path(root).joinpath(f).relative_to(base_dir)
            files.append(str(rel).replace("\\\\","/"))
    return sorted(files)

def read_file(path: pathlib.Path) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()

def write_file(path: pathlib.Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)

# -------- Mock "spec-driven" planner & agent (used if no API keys) --------
def have_llm():
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))

def llm_complete(prompt: str, system: str = "You are a helpful software engineering assistant.") -> str:
    # Use OpenAI if key provided
    # if os.environ.get("OPENAI_API_KEY") and openai:
    #     client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    #     model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    #     resp = client.chat.completions.create(
    #         model=model,
    #         messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
    #         temperature=0.2,
    #     )
    #     return resp.choices[0].message.content
    # # Use Anthropic if key provided
    # if os.environ.get("ANTHROPIC_API_KEY") and anthropic:
    #     client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    #     model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    #     resp = client.messages.create(
    #         model=model,
    #         max_tokens=2048,
    #         temperature=0.2,
    #         system=system,
    #         messages=[{"role":"user","content":prompt}],
    #     )
    #     return "".join([b.text for b in resp.content if getattr(b,"type",None)=="text"])
    # Fallback: deterministic mock
    return (
        "## Problem\n"
        + prompt.strip() + "\n\n"
        "## User Stories\n- As a user, I can view a homepage.\n- As a user, I can see a counter and increment it.\n\n"
        "## Acceptance Criteria\n- Page loads with a title.\n- Clicking the button increments the counter.\n\n"
        "## Design\n- Single-page app using vanilla JS.\n- Minimal CSS.\n\n"
        "## Tasks\n1) Create index.html\n2) Create styles.css\n3) Create app.js implementing a counter\n"
    )

def parse_spec(text: str) -> dict:
    # Parse sections into a dict
    sections = {"problem":"", "user_stories":[], "acceptance_criteria":[], "design":"", "tasks":[]}
    current = None
    for line in text.splitlines():
        m = re.match(r"^##\\s+(.*)", line.strip())
        if m:
            name = m.group(1).lower()
            if "problem" in name: current = "problem"
            elif "user stories" in name: current = "user_stories"
            elif "acceptance" in name: current = "acceptance_criteria"
            elif "design" in name: current = "design"
            elif "tasks" in name: current = "tasks"
            else: current = None
            continue
        if current == "user_stories" and line.strip().startswith("- "):
            sections["user_stories"].append(line.strip()[2:])
        elif current == "acceptance_criteria" and line.strip().startswith("- "):
            sections["acceptance_criteria"].append(line.strip()[2:])
        elif current == "tasks":
            m2 = re.match(r"^\\d+\\)\\s*(.*)", line.strip())
            if m2: sections["tasks"].append(m2.group(1))
        elif current == "problem":
            sections["problem"] += line + "\\n"
        elif current == "design":
            sections["design"] += line + "\\n"
    return sections

def apply_task_to_workspace(task: str):
    # Minimal deterministic tasks that scaffold a web app if files are missing.
    # If workspace is empty, create a vanilla JS counter page.
    files = list_files(WORKSPACE)
    if not files:
        index_html = """<!doctype html>
<html>
  <head>
    <meta charset=\\"utf-8\\"/>
    <meta name=\\"viewport\\" content=\\"width=device-width, initial-scale=1\\"/>
    <title>Kiro-Lite App</title>
    <link rel=\\"stylesheet\\" href=\\"styles.css\\">
  </head>
  <body>
    <div id=\\"app\\">
      <h1>Kiro-Lite</h1>
      <p>Ultra-minimal spec → tasks → code demo.</p>
      <button id=\\"btn\\">Count: <span id=\\"count\\">0</span></button>
    </div>
    <script src=\\"app.js\\"></script>
  </body>
</html>
"""
        styles_css = """*{box-sizing:border-box}body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:0;padding:2rem;background:#f5f5f5;color:#222}
#app{max-width:720px;margin:0 auto;background:#fff;padding:2rem;border-radius:1rem;box-shadow:0 10px 30px rgba(0,0,0,.06)}
button{padding:.7rem 1rem;border-radius:.7rem;border:1px solid #ccc;background:#fafafa;cursor:pointer}
button:active{transform:translateY(1px)}
"""
        app_js = """const btn=document.getElementById('btn');const out=document.getElementById('count');let n=0;btn.addEventListener('click',()=>{n++;out.textContent=String(n)});"""
        write_file(safe_join(WORKSPACE, "index.html"), index_html)
        write_file(safe_join(WORKSPACE, "styles.css"), styles_css)
        write_file(safe_join(WORKSPACE, "app.js"), app_js)
        return {"created":["index.html","styles.css","app.js"]}
    # Otherwise, append a comment indicating completion (placeholder)
    path = safe_join(WORKSPACE, "README.generated.md")
    old = ""
    if path.exists():
        old = read_file(path)
    write_file(path, old + f"- Completed task: {task}\n")
    return {"updated":["README.generated.md"]}

# -------- Routes --------
@app.route("/")
def root():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/spec", methods=["POST"])
def api_spec():
    data = request.get_json(force=True) or {}
    prompt = data.get("prompt","Build a tiny web app with a counter.")
    system = "You are a senior software engineer. Produce a concise but rigorous spec with sections: Problem, User Stories, Acceptance Criteria, Design, Tasks."
    text = llm_complete(prompt, system=system)
    spec = parse_spec(text)
    return jsonify({"raw": text, "spec": spec})

@app.route("/api/tasks", methods=["POST"])
def api_tasks():
    try:
        data = request.get_json(force=True) or {}
        raw = data.get("raw") or ""
        tasks = []
        for line in str(raw).splitlines():
            m = re.match(r"^\s*\d+\)\s*(.+)$", line)
            if m:
                tasks.append(m.group(1).strip())
        if not tasks:
            # fallback default tasks
            tasks = ["Create index.html", "Create styles.css", "Create app.js with a counter"]
        return jsonify({"tasks": tasks})
    except Exception as e:
        return jsonify({"error": str(e), "tasks": []}), 200


@app.route("/api/apply", methods=["POST"])
def api_apply():
    data = request.get_json(force=True) or {}
    task = data.get("task","Scaffold basic app")
    result = apply_task_to_workspace(task)
    return jsonify({"ok": True, "result": result, "workspace": list_files(WORKSPACE)})

@app.route("/api/files", methods=["GET", "POST", "DELETE"])
def api_files():
    if request.method == "GET":
        path = request.args.get("path")
        if path:
            p = safe_join(WORKSPACE, path)
            if not p.exists():
                return jsonify({"error":"not found"}), 404
            return jsonify({"path": path, "content": read_file(p)})
        return jsonify({"files": list_files(WORKSPACE)})
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        path = data.get("path")
        content = data.get("content","")
        if not path:
            return jsonify({"error":"path required"}), 400
        p = safe_join(WORKSPACE, path)
        write_file(p, content)
        return jsonify({"ok": True})
    if request.method == "DELETE":
        data = request.get_json(force=True) or {}
        path = data.get("path")
        if not path:
            return jsonify({"error":"path required"}), 400
        p = safe_join(WORKSPACE, path)
        if p.is_file():
            p.unlink()
            return jsonify({"ok": True})
        if p.is_dir():
            shutil.rmtree(p)
            return jsonify({"ok": True})
        return jsonify({"error": "not found"}), 404

@app.route("/api/download", methods=["GET"])
def api_download():
    # zip current workspace for download via browser
    zid = f"workspace-{uuid.uuid4().hex[:8]}.zip"
    zpath = WORKSPACE.parent / zid
    shutil.make_archive(str(zpath.with_suffix("")), "zip", WORKSPACE)
    return send_from_directory(str(zpath.parent), zpath.name, as_attachment=True)

# Serve static
@app.route("/static/<path:fp>")
def serve_static(fp):
    return send_from_directory(app.static_folder, fp)

if __name__ == "__main__":
    print(f"Kiro-Lite server starting on http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=True)
