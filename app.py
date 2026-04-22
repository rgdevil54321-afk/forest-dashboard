from flask import Flask, request, jsonify, session, redirect
import json, os, time, secrets, urllib.request
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

DATA_FILE   = "data.json"
ACTION_FILE = "action.json"
LOG_FILE    = "logs.txt"
USERS_FILE  = "users.json"
TOKENS_FILE = "tokens.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
BOT_SECRET        = os.environ.get("BOT_SECRET", "changeme-bot-secret")
TOKEN_TTL         = 120   # seconds until token expires


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────
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
    with open(LOG_FILE, "a") as fh:
        fh.write(f"[{stamp}] {msg}\n")

def get_users():
    u = load_json(USERS_FILE)
    if not u:
        # Seed default owner — add more users here or via users.json
        u = {"owner": {"role": "owner", "display": "Owner"}}
        save_json(USERS_FILE, u)
    return u

def purge_expired_tokens():
    tokens = load_json(TOKENS_FILE)
    now    = time.time()
    clean  = {k: v for k, v in tokens.items() if now - v["created_at"] < TOKEN_TTL}
    save_json(TOKENS_FILE, clean)
    return clean


# ─────────────────────────────────────────────────────────
# Auth decorator
# ─────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api") or request.method == "POST":
                return jsonify({"error": "Unauthorized"}), 401
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────
# Static / page routes
# ─────────────────────────────────────────────────────────
@app.route("/login")
def login_page():
    if session.get("logged_in"):
        return redirect("/")
    return open("login.html").read()

@app.route("/")
@login_required
def home():
    return open("index.html").read()

@app.route("/style.css")
def css():
    return open("style.css").read(), 200, {"Content-Type": "text/css"}

@app.route("/login.css")
def login_css():
    return open("login.css").read(), 200, {"Content-Type": "text/css"}

@app.route("/script.js")
def js():
    return open("script.js").read(), 200, {"Content-Type": "application/javascript"}


# ─────────────────────────────────────────────────────────
# Auth API
# ─────────────────────────────────────────────────────────
@app.route("/auth/login", methods=["POST"])
def auth_login():
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    token    = data.get("token", "").strip()

    if not username or not token:
        return jsonify({"ok": False, "error": "Username and token are required."}), 400

    users  = get_users()
    tokens = purge_expired_tokens()

    if username not in users:
        return jsonify({"ok": False, "error": "User not found."}), 403

    token_data = tokens.get(token)
    if not token_data:
        return jsonify({"ok": False, "error": "Invalid or expired token. Use ?dashboard in Discord to get a new one."}), 403

    if token_data.get("username") != username:
        return jsonify({"ok": False, "error": "This token was not issued for this user."}), 403

    # ✅ Consume token immediately — one-time use
    del tokens[token]
    save_json(TOKENS_FILE, tokens)

    user = users[username]
    session["logged_in"] = True
    session["username"]  = username
    session["role"]      = user.get("role", "member")
    session["display"]   = user.get("display", username)
    session.permanent    = False   # dies when browser closes

    log(f"Login ✓ → {username} [{user.get('role', 'member')}]")
    return jsonify({"ok": True})


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    u = session.get("username", "?")
    session.clear()
    log(f"Logout → {u}")
    return jsonify({"ok": True})


@app.route("/auth/me")
@login_required
def auth_me():
    return jsonify({
        "username": session.get("username"),
        "role":     session.get("role"),
        "display":  session.get("display"),
    })


# ─────────────────────────────────────────────────────────
# Bot endpoint — your Discord bot calls this to create a token
# Header:  X-Bot-Secret: <BOT_SECRET env var>
# Body:    { "username": "owner" }
# ─────────────────────────────────────────────────────────
@app.route("/bot/create_token", methods=["POST"])
def bot_create_token():
    if request.headers.get("X-Bot-Secret", "") != BOT_SECRET:
        return jsonify({"ok": False, "error": "Forbidden"}), 403

    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    users    = get_users()

    if username not in users:
        return jsonify({"ok": False, "error": f"Unknown user: {username}"}), 404

    tokens = purge_expired_tokens()
    token  = secrets.token_urlsafe(32)
    tokens[token] = {"username": username, "created_at": time.time()}
    save_json(TOKENS_FILE, tokens)

    panel_url = os.environ.get("PANEL_URL", "https://your-panel.onrender.com")
    login_url = f"{panel_url}/login?user={username}&token={token}"

    log(f"Token issued for {username} via bot")
    return jsonify({
        "ok":        True,
        "login_url": login_url,
        "expires_in": TOKEN_TTL,
    })


# ─────────────────────────────────────────────────────────
# Dashboard API — all protected
# ─────────────────────────────────────────────────────────
@app.route("/api")
@login_required
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
@login_required
def set_ip():
    data = request.get_json(silent=True) or {}
    d    = load_json(DATA_FILE)
    d["mc_ip"] = data.get("ip", "")
    save_json(DATA_FILE, d)
    log(f"IP updated → {d['mc_ip']} by {session.get('username')}")
    return jsonify({"ok": True})

@app.route("/set_max_players", methods=["POST"])
@login_required
def set_max_players():
    data = request.get_json(silent=True) or {}
    d    = load_json(DATA_FILE)
    try:
        d["max_players"] = int(data.get("max_players", 20))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Invalid value"}), 400
    save_json(DATA_FILE, d)
    log(f"Max players → {d['max_players']} by {session.get('username')}")
    return jsonify({"ok": True})

@app.route("/action", methods=["POST"])
@login_required
def action():
    data = request.get_json(silent=True) or {}
    act  = data.get("action", "")
    save_json(ACTION_FILE, {"action": act, "time": time.time()})
    log(f"Action → {act.upper()} by {session.get('username')}")

    d = load_json(DATA_FILE)
    if act == "start":     d["status"] = "Online"
    elif act == "stop":    d["status"] = "Offline"
    elif act == "restart": d["status"] = "Restarting..."
    save_json(DATA_FILE, d)
    return jsonify({"ok": True, "action": act})

@app.route("/console")
@login_required
def console():
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": "No logs yet."})
    with open(LOG_FILE) as fh:
        lines = fh.readlines()
    return jsonify({"logs": "".join(lines[-80:])})

@app.route("/console/clear", methods=["POST"])
@login_required
def clear_console():
    open(LOG_FILE, "w").close()
    log(f"Console cleared by {session.get('username')}")
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────
# AI  (protected)
# ─────────────────────────────────────────────────────────
@app.route("/ai", methods=["POST"])
@login_required
def ai():
    data = request.get_json(silent=True) or {}
    q    = data.get("q", "").strip()
    if not q:
        return jsonify({"reply": "Please enter a question."})

    d = load_json(DATA_FILE)
    server_context = f"""You are an AI assistant embedded inside a Minecraft server hosting panel called Forest Panel.
You have live access to the current server state. Use this data when answering.

=== LIVE SERVER STATE ===
Status:        {d.get('status', 'Unknown')}
Players:       {d.get('players', 0)} / {d.get('max_players', 20)} online
Server IP:     {d.get('mc_ip', 'Not configured')}
Uptime:        {d.get('uptime', 'N/A')}
Memory usage:  {d.get('memory', 'N/A')}
CPU usage:     {d.get('cpu', 'N/A')}
Version:       {d.get('version', 'Unknown')}
Logged-in user:{session.get('display', '?')} ({session.get('role', 'member')})
=========================

Answer questions about: server status, players, connecting, start/stop/restart, console logs, performance, and Minecraft help.
Be concise and friendly. Use **bold** for key values. Under 120 words unless detail is needed."""

    if not ANTHROPIC_API_KEY:
        return jsonify({"reply": "⚠️ Set `ANTHROPIC_API_KEY` on Render to enable AI."})

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
        log(f"AI → {session.get('username')}: {q[:60]}")
        return jsonify({"reply": reply})

    except Exception as e:
        log(f"AI error → {e}")
        return jsonify({"reply": f"⚠️ AI error: {str(e)}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
