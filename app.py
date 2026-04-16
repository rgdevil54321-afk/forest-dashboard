from flask import Flask, request, jsonify, Response
import json, os, time, urllib.request
from datetime import datetime

app = Flask(__name__)

DATA_FILE   = "data.json"
ACTION_FILE = "action.json"
LOG_FILE    = "logs.txt"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── helpers ──────────────────────────────────────────────
def load_json(f):
    try:
        with open(f) as fh:
            return json.load(fh)
    except:
        return {}

def save_json(f, d):
    with open(f, "w") as fh:
        json.dump(d, fh, indent=4)

def log(msg):
    stamp = datetime.now().strftime("%H:%M:%S")
    line  = f"[{stamp}] {msg}\n"
    with open(LOG_FILE, "a") as fh:
        fh.write(line)

# ── static files ─────────────────────────────────────────
@app.route("/")
def home():
    return open("index.html").read()

@app.route("/style.css")
def css():
    return open("style.css").read(), 200, {"Content-Type": "text/css"}

@app.route("/script.js")
def js():
    return open("script.js").read(), 200, {"Content-Type": "application/javascript"}

# ── API ──────────────────────────────────────────────────
@app.route("/api")
def api():
    d = load_json(DATA_FILE)
    return jsonify({
        "status":     d.get("status", "Online"),
        "players":    d.get("players", 0),
        "maxPlayers": d.get("max_players", 20),
        "ip":         d.get("mc_ip", "Not configured"),
        "uptime":     d.get("uptime", "0h 0m"),
        "memory":     d.get("memory", "0 MB"),
        "cpu":        d.get("cpu", "0%"),
        "version":    d.get("version", "Unknown"),
    })

@app.route("/set_ip", methods=["POST"])
def set_ip():
    data = request.get_json(silent=True) or {}
    d = load_json(DATA_FILE)
    d["mc_ip"] = data.get("ip", "")
    save_json(DATA_FILE, d)
    log(f"Server IP updated → {d['mc_ip']}")
    return jsonify({"ok": True})

@app.route("/set_max_players", methods=["POST"])
def set_max_players():
    data = request.get_json(silent=True) or {}
    d = load_json(DATA_FILE)
    try:
        d["max_players"] = int(data.get("max_players", 20))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Invalid value"}), 400
    save_json(DATA_FILE, d)
    log(f"Max players updated → {d['max_players']}")
    return jsonify({"ok": True})

@app.route("/action", methods=["POST"])
def action():
    data   = request.get_json(silent=True) or {}
    act    = data.get("action", "")
    save_json(ACTION_FILE, {"action": act, "time": time.time()})
    log(f"Action executed → {act.upper()}")

    d = load_json(DATA_FILE)
    if act == "start":
        d["status"] = "Online"
    elif act == "stop":
        d["status"] = "Offline"
    elif act == "restart":
        d["status"] = "Restarting..."
    save_json(DATA_FILE, d)
    return jsonify({"ok": True, "action": act})

@app.route("/console")
def console():
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": "No logs yet."})
    with open(LOG_FILE) as fh:
        lines = fh.readlines()
    return jsonify({"logs": "".join(lines[-80:])})

@app.route("/console/clear", methods=["POST"])
def clear_console():
    open(LOG_FILE, "w").close()
    log("Console cleared.")
    return jsonify({"ok": True})

# ── AI ───────────────────────────────────────────────────
@app.route("/ai", methods=["POST"])
def ai():
    data = request.get_json(silent=True) or {}
    q    = data.get("q", "").strip()
    if not q:
        return jsonify({"reply": "Please enter a question."})

    # Build real server context for Claude
    d = load_json(DATA_FILE)
    server_context = f"""You are an AI assistant embedded inside a Minecraft server hosting panel called Forest Panel.
You have live access to the current server state shown below. Use this data when answering questions.

=== LIVE SERVER STATE ===
Status:        {d.get('status', 'Unknown')}
Players:       {d.get('players', 0)} / {d.get('max_players', 20)} online
Server IP:     {d.get('mc_ip', 'Not configured')}
Uptime:        {d.get('uptime', 'N/A')}
Memory usage:  {d.get('memory', 'N/A')}
CPU usage:     {d.get('cpu', 'N/A')}
Version:       {d.get('version', 'Unknown')}
=========================

You can answer questions about: server status, player counts, how to connect, starting/stopping/restarting the server, reading console logs, server performance, Minecraft-related questions, and general hosting help.
Be concise, helpful, and friendly. Use markdown bold (**text**) for important values. Keep replies under 120 words unless a detailed explanation is clearly needed."""

    if not ANTHROPIC_API_KEY:
        # Fallback if no API key is set
        log(f"AI query (no key) → {q}")
        return jsonify({"reply": "⚠️ AI is not configured. Set the `ANTHROPIC_API_KEY` environment variable on Render to enable real AI responses."})

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "system": server_context,
            "messages": [{"role": "user", "content": q}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        reply = result["content"][0]["text"].strip()
        log(f"AI query → {q}")
        return jsonify({"reply": reply})

    except Exception as e:
        log(f"AI error → {str(e)}")
        return jsonify({"reply": f"⚠️ AI request failed: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
