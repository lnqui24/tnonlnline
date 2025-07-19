from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

users_bp = Blueprint('users', __name__)

@users_bp.route("/users")
def users():
    page = request.args.get('page', 1, type=int)
    per_page = 40
    offset = (page - 1) * per_page

    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users LIMIT ? OFFSET ?", (per_page, offset))
    users = c.fetchall()
    conn.close()

    return render_template("users.html", users=users, page=page)

@users_bp.route("/delete/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('users.users'))
