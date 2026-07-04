from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from agent import run_agent, init_db
from hardened_agent import run_agent_hardened
from auth import authenticate
import os

load_dotenv()  # carrega .env automaticamente

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "aircorp-secret-2024")
init_db()

VALID_PROVIDERS = {"fake", "claude", "openai"}


@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"])


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_info = authenticate(username, password)
        if user_info:
            session["user"] = user_info
            session["history"] = []
            session["hardened_history"] = []
            session["provider"] = "fake"          # default provider
            return redirect(url_for("index"))
        else:
            error = "Invalid credentials. Please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Provider selector ──────────────────────────────────────────────────────────
@app.route("/set_provider", methods=["POST"])
def set_provider():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json()
    provider = data.get("provider", "fake").lower()
    if provider not in VALID_PROVIDERS:
        return jsonify({"error": f"Invalid provider. Choose from: {', '.join(VALID_PROVIDERS)}"}), 400
    session["provider"] = provider
    # Reset histories when switching provider so context stays clean
    session["history"] = []
    session["hardened_history"] = []
    return jsonify({"status": "ok", "provider": provider})


@app.route("/get_provider", methods=["GET"])
def get_provider():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"provider": session.get("provider", "fake")})


# ── Vulnerable agent ───────────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json()
    user_input = data.get("message", "")
    if "history" not in session:
        session["history"] = []
    history = session["history"]
    user_context = session["user"]
    provider = session.get("provider", "fake")

    result = run_agent(user_input, history, user_context, provider=provider)
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": result["message"]})
    session["history"] = history
    return jsonify(result)


# ── Hardened agent ─────────────────────────────────────────────────────────────
@app.route("/chat_hardened", methods=["POST"])
def chat_hardened():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json()
    user_input = data.get("message", "")
    if "hardened_history" not in session:
        session["hardened_history"] = []
    history = session["hardened_history"]
    user_context = session["user"]
    provider = session.get("provider", "fake")

    result = run_agent_hardened(user_input, history, user_context, provider=provider)
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": result["message"]})
    session["hardened_history"] = history
    return jsonify(result)


# ── Reset ──────────────────────────────────────────────────────────────────────
@app.route("/reset", methods=["POST"])
def reset():
    session["history"] = []
    return jsonify({"status": "ok"})


@app.route("/reset_hardened", methods=["POST"])
def reset_hardened():
    session["hardened_history"] = []
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
