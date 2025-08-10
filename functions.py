from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Bạn cần đăng nhập để truy cập trang này.", "error")
            return redirect(url_for('login.login'))  # Chuyển về trang login
        return f(*args, **kwargs)
    return decorated_function


def ad_login_required(f):
    @wraps(f)
    def ad_decorated_function(*args, **kwargs):
        if session.get('status') != 2:
            flash("Bạn không có quyền truy cập trang này.", "error")
            return redirect(url_for('ad_login.login'))
        return f(*args, **kwargs)

    return ad_decorated_function

num_per_page = 25