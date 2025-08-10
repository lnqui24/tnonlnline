from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from functions import login_required,ad_login_required,num_per_page
import re

users_bp = Blueprint('users', __name__)

@users_bp.route('/add-teacher', methods=['POST'])
@ad_login_required
def add_teacher():
    if request.method == 'POST':
        name = request.form['name'].strip()
        username= request.form['username'].strip()
        school = request.form['school'].strip()
        sdt = request.form['sdt'].strip()
        if not sdt.isdigit() or len(sdt) != 10:
            flash(f"Số điện thoại của {name} không hợp lệ. Vui lòng nhập đúng 10 chữ số.", "error")
            return redirect(url_for('users.users'))
        if not re.fullmatch(r'0\d{9}', sdt):
            flash(f"Số điện thoại của {name} không hợp lệ. Vui lòng nhập đúng định dạng 0xxxxxxxxx.", "error")
            return redirect(url_for('users.users'))
        if not name or not school or not sdt:
            flash("Vui lòng điền đầy đủ thông tin.","error")
            return redirect(url_for('users.users'))
        try:
            conn = sqlite3.connect('student_info.db')
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Kiểm tra username hoặc sdt đã tồn tại chưa
            cur.execute("SELECT * FROM teachers WHERE username = ? OR sdt = ?", (username, sdt))
            existing = cur.fetchone()

            if existing:
                if existing['username'] == username:
                    flash('Tên đăng nhập đã tồn tại!',"error")
                elif existing['sdt'] == sdt:
                    flash('Số điện thoại đã tồn tại!',"error")
                conn.close()
                # return redirect('/register-teacher')
                return redirect(url_for('users.users'))

            # Nếu không trùng, tiến hành thêm mới
            cur.execute("INSERT INTO teachers (name, username, password, school, sdt, status) VALUES (?, ?, ?, ?, ?, ?)", 
                        (name, username, generate_password_hash('123456'), school, sdt, 0))
            conn.commit()
            conn.close()
            flash('Đăng ký thành công!',"success")
            return redirect(url_for('users.users'))

        except Exception as e:
            flash(f'Lỗi khi đăng ký: {str(e)}')
            # return redirect('/register-teacher')
            return redirect(url_for('users.users'))


    # return render_template('register_teacher.html')
    return redirect(url_for('users.users'))

@users_bp.route("/users")
@ad_login_required
def users():
    username_ss = session.get("username", "Ẩn danh")
    page = request.args.get('page', 1, type=int)
    per_page = 40
    offset = (page - 1) * per_page

    default_password = '123456'
    
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    c.execute("SELECT * FROM teachers LIMIT ? OFFSET ?", (per_page, offset))
    raw_users = c.fetchall()
    conn.close()

    users = []
    for user in raw_users:
        user_id = user[0]
        username = user[1]
        hashed_pw = user[2]
        name = user[3]
        school = user[4]
        sdt = user[5]
        status = user[6]
        re_pw = user[7]

        try:
            # is_default = check_password_hash(hashed_pw, default_password)
            is_default = (re_pw != 1)
        except:
            is_default = False

        display_pw = default_password if is_default else "******"
        if status == 2: display_pw = "******"
        users.append({
            'id': user_id,
            'username': username,
            'password': display_pw,
            'name': name,
            'school': school,
            'sdt': sdt,
            'status': status
        })

    return render_template("users.html", users=users, page=page, username_ss=username_ss )

@users_bp.route("/unlock/<int:user_id>", methods=["POST"])
@ad_login_required
def unlock_user(user_id):
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    c.execute("UPDATE teachers SET status = 1 WHERE id = ?", (user_id,))
    flash("Đã mở khóa tài khoản!", "success")
    conn.commit()
    conn.close()
    return redirect(url_for('users.users'))

@users_bp.route("/lock/<int:user_id>", methods=["POST"])
@ad_login_required
def lock_user(user_id):
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    c.execute("UPDATE teachers SET status = 0 WHERE id = ?", (user_id,))
    flash("Đã khóa tài khoản thành công!", "success")
    conn.commit()
    conn.close()
    return redirect(url_for('users.users'))

@users_bp.route("/delete/<int:user_id>", methods=["POST"])
@ad_login_required
def delete_user(user_id):
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    conn.execute("PRAGMA foreign_keys = ON;")
    c.execute("DELETE FROM teachers WHERE id = ?", (user_id,))
    flash("Đã xóa tài khoản thành công!", "success")
    conn.commit()
    conn.close()
    return redirect(url_for('users.users'))

@users_bp.route("/repass/<int:user_id>", methods=["POST"])
@ad_login_required
def repass(user_id):
    default_password = "123456"
    hashed_pw = generate_password_hash(default_password)
    conn = None
    try:
        conn = sqlite3.connect('student_info.db')
        c = conn.cursor()
        c.execute("UPDATE teachers SET password = ?, re_pw = ? WHERE id = ?", (hashed_pw, 0, user_id))
        c.execute("SELECT username, name FROM teachers WHERE id = ?", (user_id,))
        user = c.fetchone()
        username, name = user
        conn.commit()
        flash("Đã đặt lại mật khẩu cho " + name, "success")
    except Exception as e:
        print("Lỗi khi đặt lại mật khẩu:", e)
        flash("Có lỗi xảy ra khi đặt lại mật khẩu!", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for('users.users'))

@users_bp.route("/change-password", methods=["POST"])
@login_required  # chỉ cho user đã đăng nhập
def change_password():
    old_password = request.form.get("old_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    # Lấy username từ session
    username_ss = session.get("username")

    if not username_ss:
        flash("Bạn cần đăng nhập để đổi mật khẩu!", "error")
        return redirect(url_for("login.login"))

    if not old_password or not new_password or not confirm_password:
        flash("Vui lòng nhập đầy đủ thông tin!", "error")
        return redirect(url_for("upload.danh_sach_de_thi"))

    if new_password != confirm_password:
        flash("Mật khẩu mới nhập lại không khớp!", "error")
        return redirect(url_for("upload.danh_sach_de_thi"))

    try:
        conn = sqlite3.connect('student_info.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Lấy hash mật khẩu hiện tại
        cur.execute("SELECT password, status FROM teachers WHERE username = ?", (username_ss,))
        user = cur.fetchone()

        if user['status'] == 0:
            flash("Không đổi được mật khẩu vì đang bị khóa!", "error")
            conn.close()
            return redirect(url_for("upload.danh_sach_de_thi"))

        if not user:
            flash("Tài khoản không tồn tại!", "error")
            conn.close()
            return redirect(url_for("upload.danh_sach_de_thi"))

        hashed_pw = user["password"]

        # Kiểm tra mật khẩu cũ
        if not check_password_hash(hashed_pw, old_password):
            flash("Mật khẩu hiện tại không đúng!", "error")
            conn.close()
            return redirect(url_for("upload.danh_sach_de_thi"))

        # Cập nhật mật khẩu mới
        new_hashed_pw = generate_password_hash(new_password)
        cur.execute("UPDATE teachers SET password = ?, re_pw = ? WHERE username = ?", (new_hashed_pw, 1, username_ss))
        conn.commit()
        conn.close()

        flash("Đổi mật khẩu thành công!", "success")
    except Exception as e:
        flash(f"Có lỗi xảy ra: {str(e)}", "error")

    return redirect(url_for("upload.danh_sach_de_thi"))
