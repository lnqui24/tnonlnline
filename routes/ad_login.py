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
from functions import num_per_page, ad_login_required
from math import ceil

ad_login_bp = Blueprint('ad_login', __name__)


# VALID_USERS = {
#     "admin": "123456",
#     "teacher": "giaovien"
# }

# @ad_login_bp.route('/admincp', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form.get('username')
#         password = request.form.get('password')
#         if username in VALID_USERS and VALID_USERS[username] == password:
#             session['username'] = username
#             flash('Đăng nhập thành công!', 'success')
#             return redirect(url_for('upload.danh_sach_de_thi'))
#         else:
#             flash('Sai tên đăng nhập hoặc mật khẩu.', 'error')
#     return render_template('login.html')

@ad_login_bp.route('/admincp', methods=['GET', 'POST'])
def login():
    user_st = session.get("status")
    username = session.get("username","Ẩn Danh")
    print(user_st, username)
    if user_st == 2:        
        # return render_template('ad_quanli_dethi.html', username=username)
        return redirect(url_for('ad_login.addanh_sach_de_thi'))
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
            if status != 2:
                flash("Tài khoản của bạn đang bị khóa hoặc không là admin.", "error")
                return redirect(url_for('ad_login.login'))

            # Kiểm tra mật khẩu
            if check_password_hash(hashed_pw, password):
                # Lưu session
                session['user_id'] = user_id
                session['username'] = username_db
                session['name'] = name
                session['school'] = school
                session['status'] = status

                flash("Đăng nhập thành công!", "success")
                return redirect(url_for('ad_login.addanh_sach_de_thi'))  # Hoặc route bạn muốn
                # return render_template('ad_quanli_dethi.html', username=username)
            else:
                flash("Sai mật khẩu.", "error")
        else:
            flash("Tài khoản không tồn tại.", "error")

    return render_template('ad_login.html')


@ad_login_bp.route('/ad_logout')
def logout():
    session.clear()
    flash("Bạn đã đăng xuất!", "success")
    return redirect(url_for('ad_login.login'))

@ad_login_bp.route('/create_super_admin')
def create_super_admin():
    username = 'admin'
    password = 'qui03048'
    hashed_pw = generate_password_hash(password)

    name = 'Super Admin(LNQ)'
    school = 'THPT Châu Văn Liêm'
    sdt = '0982203048'
    status = 2  # super_admin
    re_pw = 0

    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()

    # Kiểm tra nếu username đã tồn tại
    c.execute("DELETE FROM teachers WHERE username = ?", (username,))
    # Thêm tài khoản mới
    c.execute('''
        INSERT INTO teachers (id, username, password, name, school, sdt, status, re_pw)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (1,username, hashed_pw, name, school, sdt, status,re_pw))
    conn.commit()
    conn.close()

    flash("Tài khoản super_admin đã được tạo lại!", "success")
    return redirect(url_for('ad_login.login'))
@ad_login_bp.route('/addanh-sach-de-thi')
@ad_login_required
def addanh_sach_de_thi():
    username = session.get("username", "Ẩn danh")
    search_id = request.args.get('search_id', '').strip()
    page = request.args.get('page', 1, type=int)  # Trang hiện tại (mặc định = 1)
    per_page = num_per_page  # Số bản ghi mỗi trang

    offset = (page - 1) * per_page

    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()

    # Đếm tổng số đề thi để tính số trang
    if search_id:
        c.execute('SELECT COUNT(*) FROM dethi WHERE id LIKE ?', (f'%{search_id}%',))
    else:
        c.execute('SELECT COUNT(*) FROM dethi')
    total_rows = c.fetchone()[0]
    total_pages = ceil(total_rows / per_page)

    # Lấy danh sách đề thi theo trang
    if search_id:
        c.execute('''
            SELECT d.id, d.ten_dethi, d.so_cau, d.dap_an, d.time, d.id_dapan, d.action, d.xt_hs, d.time_create,
                   COUNT(b.id_hocsinh) as sl_hs
            FROM dethi d
            LEFT JOIN baithi b ON d.id = b.id_dethi
            WHERE d.id LIKE ?
            GROUP BY d.id
            ORDER BY d.time_create DESC
            LIMIT ? OFFSET ?
        ''', (f'%{search_id}%', per_page, offset))
    else:
        c.execute('''
            SELECT d.id, d.ten_dethi, d.so_cau, d.dap_an, d.time, d.id_dapan, d.action, d.xt_hs, d.time_create,
                   COUNT(b.id_hocsinh) as sl_hs
            FROM dethi d
            LEFT JOIN baithi b ON d.id = b.id_dethi
            GROUP BY d.id
            ORDER BY d.time_create DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))

    rows = c.fetchall()
    conn.close()

    return render_template(
        'ad_quanli_dethi.html',
        dethi_list=rows,
        username=username,
        page=page,
        total_pages=total_pages,
        search_id=search_id
    )

@ad_login_bp.route('/cleandb')
@ad_login_required
def cleandb():
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    conn.execute('VACUUM')
    flash("Đã dọn dẹp csdl", "sucess")
    conn.close()
    return render_template('ad_login.html')