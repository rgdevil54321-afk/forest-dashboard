from flask import Flask, request, jsonify
import json

app = Flask(__name__)

DATA_FILE = "data.json"

def load():
    try:
        return json.load(open(DATA_FILE))
    except:
        return {}

def save(d):
    json.dump(d, open(DATA_FILE, "w"), indent=4)

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/style.css")
def css():
    return open("style.css").read(), 200, {'Content-Type':'text/css'}

@app.route("/script.js")
def js():
    return open("script.js").read(), 200, {'Content-Type':'application/javascript'}

@app.route("/api")
def api():
    d = load()
    return {
        "status": "Online",
        "players": d.get("players", 0),
        "ip": d.get("mc_ip", "Not Set")
    }

@app.route("/set_ip", methods=["POST"])
def set_ip():
    data = request.json
    d = load()
    d["mc_ip"] = data.get("ip")
    save(d)
    return {"ok": True}

# ACTION SYSTEM
@app.route("/action", methods=["POST"])
def action():
    data = request.json
    json.dump({"action": data.get("action")}, open("action.json", "w"))
    return {"ok": True}

# CONSOLE
@app.route("/console")
def console():
    try:
        logs = open("logs.txt").read()
    except:
        logs = "No logs yet"
    return {"logs": logs}

# FAKE AI (we upgrade later)
@app.route("/ai", methods=["POST"])
def ai():
    q = request.json.get("q")
    return {"reply": f"AI: You said -> {q}"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
