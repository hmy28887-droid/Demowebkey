from flask import Flask, render_template, request, redirect, session, jsonify
import uuid
import hashlib
import datetime
import os

app = Flask(__name__)
app.secret_key = "super-secret-key-change-this"

# ====== CONFIG ADMIN ======
ADMIN_USER = "admin"
ADMIN_PASS = "123456"   # <-- ĐỔI Ở ĐÂY

# ====== DATABASE MEMORY ======
keys_db = {}

# ====== UTIL ======
def generate_key():
    return str(uuid.uuid4()).replace("-", "").upper()[:16]

# ====== ROUTES ======

@app.route("/")
def home():
    if "admin" not in session:
        return redirect("/login")
    return render_template("dashboard.html", keys=keys_db)

@app.route("/login", methods=["GET","POST"])
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

@app.route("/create")
def create():
    key = generate_key()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=1)

    keys_db[key] = {
        "device": None,
        "expire": expire,
        "active": True
    }
    return redirect("/")

@app.route("/toggle/<key>")
def toggle(key):
    if key in keys_db:
        keys_db[key]["active"] = not keys_db[key]["active"]
    return redirect("/")

@app.route("/delete/<key>")
def delete(key):
    if key in keys_db:
        del keys_db[key]
    return redirect("/")

# ===== API CHECK =====

@app.route("/api/check", methods=["POST"])
def api_check():
    data = request.json
    key = data.get("key")
    device = data.get("device")

    if key not in keys_db:
        return jsonify({"status":"invalid"})

    k = keys_db[key]

    if not k["active"]:
        return jsonify({"status":"disabled"})

    if datetime.datetime.utcnow() > k["expire"]:
        return jsonify({"status":"expired"})

    # Giới hạn 1 thiết bị thật
    if k["device"] is None:
        k["device"] = device
    elif k["device"] != device:
        return jsonify({"status":"device_limit"})

    return jsonify({"status":"ok"})

# ===== RUN =====

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
  
