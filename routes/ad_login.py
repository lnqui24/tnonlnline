from flask import Blueprint, render_template, request, current_app, jsonify
from flask import redirect, url_for, flash
from werkzeug.utils import secure_filename
from docx_reader_math import (read_questions_from_docx, InvalidDocxFile, FileLockedError, XMLParseError)
from datetime import datetime
import os, sqlite3, json
import random, glob
import string
from flask import Flask, render_template, request, redirect, url_for, flash, session
ad_login_bp = Blueprint('ad_login', __name__)


VALID_USERS = {
    "admin": "123456",
    "teacher": "giaovien"
}

@ad_login_bp.route('/admincp', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in VALID_USERS and VALID_USERS[username] == password:
            session['username'] = username
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('upload.danh_sach_de_thi'))
        else:
            flash('Sai tên đăng nhập hoặc mật khẩu.', 'error')
    return render_template('login.html')


@ad_login_bp.route('/logout')
def logout():
    session.clear()
    flash("Bạn đã đăng xuất!", "success")
    return redirect(url_for('ad_login.login'))
