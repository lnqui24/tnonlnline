from flask import Blueprint, render_template, request, current_app, jsonify
from flask import redirect, url_for, flash
from werkzeug.utils import secure_filename
from docx_reader_math import (read_questions_from_docx, InvalidDocxFile, FileLockedError, XMLParseError)
from datetime import datetime
import os, sqlite3, json
import random, glob
import string
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re

re_teachers_bp = Blueprint('re_teachers', __name__)

@re_teachers_bp.route('/register-teacher', methods=['GET', 'POST'])
def register_teacher():
    if request.method == 'POST':
        name = request.form['name'].strip()
        username= request.form['username'].strip()
        school = request.form['school'].strip()
        sdt = request.form['sdt'].strip()
        if not sdt.isdigit() or len(sdt) != 10:
            flash(f"Số điện thoại của {name} không hợp lệ. Vui lòng nhập đúng 10 chữ số.", "error")
            # return redirect(url_for('users.users'))
            return render_template("register_teacher.html")
        if not re.fullmatch(r'0\d{9}', sdt):
            flash(f"Số điện thoại của {name} không hợp lệ. Vui lòng nhập đúng định dạng 0xxxxxxxxx.", "error")
            # return redirect(url_for('users.users'))
            return render_template("register_teacher.html")
        if not name or not school or not sdt:
            flash("Vui lòng điền đầy đủ thông tin.","error")
            # return redirect(url_for('users.users'))
            return render_template("register_teacher.html")
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
                    return render_template("register_teacher.html")
                elif existing['sdt'] == sdt:
                    flash('Số điện thoại đã tồn tại!',"error")
                    return render_template("register_teacher.html")
                conn.close()
                return render_template("register_teacher.html")
                # return redirect(url_for('users.users'))

            # Nếu không trùng, tiến hành thêm mới
            cur.execute("INSERT INTO teachers (name, username, password, school, sdt, status) VALUES (?, ?, ?, ?, ?, ?)", 
                        (name, username, generate_password_hash('123456'), school, sdt, 0))
            conn.commit()
            conn.close()
            flash('Đăng ký thành công!',"success")
            # return redirect('/register-teacher')
            return redirect(url_for('login.login'))

        except Exception as e:
            flash(f'Lỗi khi đăng ký: {str(e)}')
            # return redirect('/register-teacher')
            return redirect(url_for('login.login'))


    # return render_template('register_teacher.html')
    # return redirect(url_for('users.users'))
    return redirect(url_for('login.login'))

@re_teachers_bp.route('/register')
def register():
    return render_template("register_teacher.html")
