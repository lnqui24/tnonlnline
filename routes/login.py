from flask import Blueprint, render_template, request, current_app, jsonify
from flask import redirect, url_for, flash
from werkzeug.utils import secure_filename
from docx_reader_math import (read_questions_from_docx, InvalidDocxFile, FileLockedError, XMLParseError)
from datetime import datetime
import os, sqlite3, json
import random, glob
import string
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    username = session.get("username")
    if username:
        # return render_template('quanli_dethi.html', username=username)
        return redirect(url_for('upload.danh_sach_de_thi'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Kết nối CSDL
        conn = sqlite3.connect('student_info.db')
        c = conn.cursor()
        c.execute("SELECT id, username, password, name, school, sdt, status FROM teachers WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user:
            user_id, username_db, hashed_pw, name, school, sdt, status = user

            # Kiểm tra trạng thái
            if status == 0:
                flash("Tài khoản của bạn đang bị khóa, liên hệ Admin.", "error")
                return redirect(url_for('login.login'))

            # Kiểm tra mật khẩu
            if check_password_hash(hashed_pw, password):
                # Lưu session
                session['user_id'] = user_id
                session['username'] = username_db
                session['name'] = name
                session['school'] = school
                session['status'] = status
                session['teacher_id'] = user_id

                flash("Đăng nhập thành công!", "success")
                # return redirect(url_for('upload.danh_sach_de_thi'))  # Hoặc route bạn muốn
                # return render_template('quanli_dethi.html', username=username)
                return redirect(url_for('upload.danh_sach_de_thi'))
            else:
                flash("Sai mật khẩu.", "error")
        else:
            flash("Tài khoản không tồn tại.", "error")

    return render_template('login.html')


@login_bp.route('/logout')
def logout():
    session.clear()
    flash("Bạn đã đăng xuất!", "success")
    return redirect(url_for('login.login'))
