import os
import logging
import traceback
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv

import database

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.getenv("WEB_PASSWORD", "change-me")

PASSWORD = os.getenv("WEB_PASSWORD", "admin")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/health")
def health():
    return "ok"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("panel"))
        return render_template("login.html", error="Wrong password")
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def panel():
    try:
        users = database.get_all_users()
        stats = database.get_stats()
        return render_template("panel.html", users=users, stats=stats)
    except Exception as e:
        logging.error(traceback.format_exc())
        return f"Error: {e}", 500


@app.route("/user/<int:user_id>")
@login_required
def user_detail(user_id):
    try:
        users = database.get_all_users()
        user = next((u for u in users if u["user_id"] == user_id), None)
        if not user:
            return "User not found", 404
        actions = database.get_user_actions(user_id)
        return render_template("user_detail.html", user=user, actions=actions)
    except Exception as e:
        logging.error(traceback.format_exc())
        return f"Error: {e}", 500


@app.route("/api/users")
@login_required
def api_users():
    users = database.get_all_users()
    return jsonify([dict(u) for u in users])


if __name__ == "__main__":
    database.init_db()
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
