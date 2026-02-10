import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================

app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "nam0303")

DATA_FILE = "keys.json"


# ==============================
# UTIL
# ==============================

def load_keys():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_keys(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def auto_disable_expired(keys):
    now = datetime.utcnow()
    changed = False

    for k, v in keys.items():
        if v["active"]:
            expire = datetime.fromisoformat(v["expires"])
            if now > expire:
                v["active"] = False
                changed = True

    if changed:
        save_keys(keys)

    return keys


# ==============================
# ROUTES
# ==============================

@app.route("/")
def home():
    if not session.get("admin"):
        return redirect("/login")

    keys = load_keys()
    keys = auto_disable_expired(keys)
    now = datetime.utcnow()

    return render_template("index.html", keys=keys, now=now)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")

        if user == ADMIN_USER and pw == ADMIN_PASS:
            session["admin"] = True
            return redirect("/")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/create", methods=["POST"])
def create():
    if not session.get("admin"):
        return redirect("/login")

    duration = int(request.form.get("hours", 24))

    keys = load_keys()

    new_key = uuid.uuid4().hex[:16].upper()

    keys[new_key] = {
        "device": None,
        "expires": (datetime.utcnow() + timedelta(hours=duration)).isoformat(),
        "active": True
    }

    save_keys(keys)
    return redirect("/")


@app.route("/delete/<key>")
def delete(key):
    if not session.get("admin"):
        return redirect("/login")

    keys = load_keys()
    if key in keys:
        del keys[key]
        save_keys(keys)

    return redirect("/")


@app.route("/toggle/<key>")
def toggle(key):
    if not session.get("admin"):
        return redirect("/login")

    keys = load_keys()
    if key in keys:
        keys[key]["active"] = not keys[key]["active"]
        save_keys(keys)

    return redirect("/")


# ==============================
# API CHECK KEY (CHO SCRIPT / EXE)
# ==============================

@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.json
    key = data.get("key")
    device = data.get("device")

    keys = load_keys()
    keys = auto_disable_expired(keys)

    if key not in keys:
        return jsonify({"status": "invalid"})

    k = keys[key]

    if not k["active"]:
        return jsonify({"status": "expired"})

    expire_time = datetime.fromisoformat(k["expires"])
    if datetime.utcnow() > expire_time:
        k["active"] = False
        save_keys(keys)
        return jsonify({"status": "expired"})

    # Giới hạn 1 thiết bị thật
    if k["device"] is None:
        k["device"] = device
        save_keys(keys)
    elif k["device"] != device:
        return jsonify({"status": "device_limit"})

    remaining = int((expire_time - datetime.utcnow()).total_seconds())

    return jsonify({
        "status": "valid",
        "remaining_seconds": remaining
    })


# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
