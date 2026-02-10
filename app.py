import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, session

app = Flask(__name__)
app.secret_key = "supersecret123"

KEYS_FILE = "keys.json"


# ================= UTIL =================

def load_keys():
    if not os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "w") as f:
            json.dump({}, f)
    with open(KEYS_FILE, "r") as f:
        return json.load(f)


def save_keys(data):
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def auto_disable_expired():
    keys = load_keys()
    now = datetime.utcnow()

    for key in keys:
        if keys[key]["expire"]:
            expire_time = datetime.fromisoformat(keys[key]["expire"])
            if now > expire_time:
                keys[key]["active"] = False

    save_keys(keys)


# ================= ROUTES =================

@app.route("/")
def home():
    if "admin" not in session:
        return redirect("/login")

    auto_disable_expired()
    keys = load_keys()
    return render_template("index.html", keys=keys)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "hoangnam0303":
            session["admin"] = True
            return redirect("/")
        else:
            return "Sai tài khoản"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/create", methods=["POST"])
def create_key():
    if "admin" not in session:
        return redirect("/login")

    key = request.form["key"]
    days = int(request.form["days"])

    keys = load_keys()

    expire_time = datetime.utcnow() + timedelta(days=days)

    keys[key] = {
        "device": None,
        "expire": expire_time.isoformat(),
        "active": True
    }

    save_keys(keys)
    return redirect("/")


@app.route("/toggle/<key>")
def toggle_key(key):
    keys = load_keys()
    if key in keys:
        keys[key]["active"] = not keys[key]["active"]
        save_keys(keys)
    return redirect("/")


@app.route("/delete/<key>")
def delete_key(key):
    keys = load_keys()
    if key in keys:
        del keys[key]
        save_keys(keys)
    return redirect("/")


# ================= API =================

@app.route("/api/check", methods=["POST"])
def check_key():
    auto_disable_expired()

    data = request.json
    key = data.get("key")
    device = data.get("device")

    keys = load_keys()

    if key not in keys:
        return jsonify({"status": "invalid"})

    if not keys[key]["active"]:
        return jsonify({"status": "disabled"})

    if keys[key]["device"] is None:
        keys[key]["device"] = device
        save_keys(keys)
    elif keys[key]["device"] != device:
        return jsonify({"status": "device_mismatch"})

    return jsonify({"status": "valid"})


# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
