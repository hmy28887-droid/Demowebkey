import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me"

DATA_FILE = "keys.json"


# =========================
# Load / Save
# =========================

def load_keys():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
        return {}

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_keys(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# Helper
# =========================

def auto_disable_expired(keys):
    now = datetime.utcnow()
    changed = False

    for k, v in keys.items():
        if v["active"]:
            expire_time = datetime.fromisoformat(v["expire"])
            if now > expire_time:
                v["active"] = False
                changed = True

    if changed:
        save_keys(keys)


# =========================
# Login
# =========================

ADMIN_USER = "admin"
ADMIN_PASS = "hoangnam0303"


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin"] = True
            return redirect("/dashboard")

    return render_template("login.html")


# =========================
# Dashboard
# =========================

@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/")

    keys = load_keys()
    auto_disable_expired(keys)

    return render_template(
        "dashboard.html",
        keys=keys,
        now=datetime.utcnow()
    )


@app.route("/create", methods=["POST"])
def create_key():
    if not session.get("admin"):
        return redirect("/")

    keys = load_keys()

    key_value = request.form.get("key")
    days = int(request.form.get("days", 1))

    expire_time = datetime.utcnow() + timedelta(days=days)

    keys[key_value] = {
        "device": None,
        "expire": expire_time.isoformat(),
        "active": True
    }

    save_keys(keys)
    return redirect("/dashboard")


@app.route("/toggle/<key>")
def toggle_key(key):
    if not session.get("admin"):
        return redirect("/")

    keys = load_keys()

    if key in keys:
        keys[key]["active"] = not keys[key]["active"]
        save_keys(keys)

    return redirect("/dashboard")


@app.route("/delete/<key>")
def delete_key(key):
    if not session.get("admin"):
        return redirect("/")

    keys = load_keys()

    if key in keys:
        del keys[key]
        save_keys(keys)

    return redirect("/dashboard")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# API CHECK
# =========================

@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.json
    key = data.get("key")
    device_id = data.get("device_id")

    keys = load_keys()
    auto_disable_expired(keys)

    if key not in keys:
        return jsonify({"status": "invalid"})

    key_data = keys[key]

    if not key_data["active"]:
        return jsonify({"status": "invalid"})

    expire_time = datetime.fromisoformat(key_data["expire"])

    if datetime.utcnow() > expire_time:
        key_data["active"] = False
        save_keys(keys)
        return jsonify({"status": "expired"})

    # Giới hạn 1 thiết bị
    if key_data["device"] is None:
        key_data["device"] = device_id
        save_keys(keys)
    elif key_data["device"] != device_id:
        return jsonify({"status": "device_locked"})

    return jsonify({"status": "valid"})


# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
