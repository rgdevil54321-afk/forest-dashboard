from flask import Flask, request, jsonify, Response
import json, os, time
from datetime import datetime

app = Flask(__name__)

DATA_FILE   = "data.json"
ACTION_FILE = "action.json"
LOG_FILE    = "logs.txt"

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
        "status":  d.get("status", "Online"),
        "players": d.get("players", 0),
        "maxPlayers": d.get("max_players", 20),
        "ip":      d.get("mc_ip", "Not configured"),
        "uptime":  d.get("uptime", "0h 0m"),
        "memory":  d.get("memory", "0 MB"),
        "cpu":     d.get("cpu", "0%"),
        "version": d.get("version", "Unknown"),
    })

@app.route("/set_ip", methods=["POST"])
def set_ip():
    data = request.get_json(silent=True) or {}
    d = load_json(DATA_FILE)
    d["mc_ip"] = data.get("ip", "")
    save_json(DATA_FILE, d)
    log(f"Server IP updated → {d['mc_ip']}")
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
    # Return last 80 lines
    return jsonify({"logs": "".join(lines[-80:])})

@app.route("/console/clear", methods=["POST"])
def clear_console():
    open(LOG_FILE, "w").close()
    log("Console cleared.")
    return jsonify({"ok": True})

@app.route("/ai", methods=["POST"])
def ai():
    data = request.get_json(silent=True) or {}
    q    = data.get("q", "").strip()
    if not q:
        return jsonify({"reply": "Please enter a question."})

    q_lower = q.lower()
    if any(w in q_lower for w in ["status", "online", "offline"]):
        reply = "The server status is checked via the Dashboard tab. It refreshes automatically every 3 seconds."
    elif any(w in q_lower for w in ["ip", "address", "connect"]):
        d = load_json(DATA_FILE)
        ip = d.get("mc_ip", "Not configured")
        reply = f"The server IP is currently set to: **{ip}**. You can update it in the Control tab."
    elif any(w in q_lower for w in ["start", "stop", "restart"]):
        reply = "Use the Control tab to Start, Stop, or Restart your server. Actions are logged in real-time."
    elif any(w in q_lower for w in ["players", "who", "how many"]):
        d = load_json(DATA_FILE)
        reply = f"Currently {d.get('players', 0)} players are online."
    elif any(w in q_lower for w in ["log", "console", "error"]):
        reply = "Check the Console tab for real-time logs. The console auto-refreshes every 2 seconds."
    elif any(w in q_lower for w in ["help", "what", "how"]):
        reply = "I can help with: server status, IP settings, player count, starting/stopping the server, and reading logs. Just ask!"
    else:
        reply = f"Got your message: \"{q}\". For now I handle server-related queries. Try asking about status, IP, players, or controls."

    log(f"AI query → {q}")
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
