from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me"

DATA_FILE = "keys.json"

# =========================
# Load / Save Keys
# =========================
def load_keys():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

keys = load_keys()

# =========================
# Auto disable expired keys
# =========================
def check_expired():
    changed = False
    now = datetime.now()

    for k in keys:
        exp = datetime.fromisoformat(keys[k]["expires_at"])
        if now > exp and keys[k]["active"]:
            keys[k]["active"] = False
            changed = True

    if changed:
        save_keys(keys)

# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "hoangnam0804":
            session["admin"] = True
            return redirect("/dashboard")

    return render_template("login.html")

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/")

    check_expired()
    return render_template("dashboard.html", keys=keys, now=datetime.now())

# =========================
# CREATE KEY
# =========================
@app.route("/create", methods=["POST"])
def create_key():
    if not session.get("admin"):
        return redirect("/")

    key = request.form.get("key")
    days = int(request.form.get("days"))

    keys[key] = {
        "device_id": None,
        "device_name": None,
        "expires_at": (datetime.now() + timedelta(days=days)).isoformat(),
        "active": True
    }

    save_keys(keys)
    return redirect("/dashboard")

# =========================
# TOGGLE
# =========================
@app.route("/toggle/<key>")
def toggle(key):
    if key in keys:
        keys[key]["active"] = not keys[key]["active"]
        save_keys(keys)

    return redirect("/dashboard")

# =========================
# DELETE
# =========================
@app.route("/delete/<key>")
def delete(key):
    if key in keys:
        del keys[key]
        save_keys(keys)

    return redirect("/dashboard")

# =========================
# API CHECK (QUAN TRỌNG)
# =========================
@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.json
    key = data.get("key")
    device_id = data.get("device_id")
    device_name = data.get("device_name")

    if key not in keys:
        return jsonify({"status": "invalid", "message": "Key không tồn tại"})

    key_data = keys[key]

    # Hết hạn
    if datetime.now() > datetime.fromisoformat(key_data["expires_at"]):
        key_data["active"] = False
        save_keys(keys)
        return jsonify({"status": "expired", "message": "Key đã hết hạn"})

    if not key_data["active"]:
        return jsonify({"status": "disabled", "message": "Key đã bị tắt"})

    # Nếu chưa gắn thiết bị
    if not key_data["device_id"]:
        key_data["device_id"] = device_id
        key_data["device_name"] = device_name
        save_keys(keys)

    # Nếu khác thiết bị
    elif key_data["device_id"] != device_id:
        return jsonify({
            "status": "invalid",
            "message": "Key đã được dùng trên thiết bị khác"
        })

    return jsonify({
        "status": "valid",
        "device": key_data["device_name"]
    })


# =========================
# RUN (QUAN TRỌNG CHO RENDER)
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
