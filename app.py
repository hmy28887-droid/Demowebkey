from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime, timedelta, timezone
import secrets
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# ===== CONFIG ADMIN =====
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "hoangnam0804")

DATA_FILE = "keys.json"


# =============================
# LOAD & SAVE
# =============================

def load_keys():
    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_keys(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =============================
# AUTO DISABLE EXPIRED KEYS
# =============================

def auto_disable_expired():
    keys = load_keys()
    now = datetime.now(timezone.utc)
    changed = False

    for key, data in keys.items():
        if data["active"]:
            expire_time = datetime.fromisoformat(data["expire"])
            if now > expire_time:
                data["active"] = False
                changed = True

    if changed:
        save_keys(keys)


# =============================
# LOGIN
# =============================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")

        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session["admin"] = True
            return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =============================
# ADMIN PANEL
# =============================

@app.route("/")
def home():
    if not session.get("admin"):
        return redirect("/login")

    auto_disable_expired()
    keys = load_keys()

    return render_template("index.html", keys=keys)


# =============================
# CREATE KEY
# =============================

@app.route("/create", methods=["POST"])
def create_key():
    if not session.get("admin"):
        return redirect("/login")

    hours = int(request.form.get("hours", 24))

    expire_time = datetime.now(timezone.utc) + timedelta(hours=hours)
    new_key = secrets.token_hex(8).upper()

    keys = load_keys()

    keys[new_key] = {
        "device": None,
        "expire": expire_time.isoformat(),
        "active": True
    }

    save_keys(keys)
    return redirect("/")


# =============================
# DELETE KEY
# =============================

@app.route("/delete/<key>")
def delete_key(key):
    if not session.get("admin"):
        return redirect("/login")

    keys = load_keys()
    if key in keys:
        del keys[key]
        save_keys(keys)

    return redirect("/")


# =============================
# TOGGLE KEY
# =============================

@app.route("/toggle/<key>")
def toggle_key(key):
    if not session.get("admin"):
        return redirect("/login")

    keys = load_keys()
    if key in keys:
        keys[key]["active"] = not keys[key]["active"]
        save_keys(keys)

    return redirect("/")


# =============================
# API CHECK (CHO EXE / SCRIPT)
# =============================

@app.route("/api/check", methods=["POST"])
def api_check():
    auto_disable_expired()

    data = request.json
    if not data:
        return jsonify({"success": False, "message": "No data"})

    key = data.get("key")
    device = data.get("device")

    keys = load_keys()

    if key not in keys:
        return jsonify({"success": False, "message": "Key không tồn tại"})

    key_data = keys[key]

    if not key_data["active"]:
        return jsonify({"success": False, "message": "Key đã bị tắt hoặc hết hạn"})

    now = datetime.now(timezone.utc)
    expire_time = datetime.fromisoformat(key_data["expire"])

    if now > expire_time:
        key_data["active"] = False
        save_keys(keys)
        return jsonify({"success": False, "message": "Key đã hết hạn"})

    # ===== GIỚI HẠN 1 THIẾT BỊ =====
    if key_data["device"] is None:
        key_data["device"] = device
        save_keys(keys)
    elif key_data["device"] != device:
        return jsonify({"success": False, "message": "Key đã dùng trên thiết bị khác"})

    return jsonify({
        "success": True,
        "message": "Key hợp lệ",
        "expire": key_data["expire"]
    })


# =============================
# RUN
# =============================

if __name__ == "__main__":
    app.run(debug=True)
           
