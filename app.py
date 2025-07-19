from flask import Flask
import os
import sqlite3

from routes.main import main_bp
from routes.quiz import quiz_bp
from routes.users import users_bp
from routes.upload import upload_bp
from routes.xuli_dethi import xuli_dethi_bp
from routes.cham_bai import cham_bai_bp
from routes.xuat_excel import xuat_excel_bp

from docx_reader import read_questions_from_docx

app = Flask(__name__)
app.secret_key = 'lnqui24_cvl'  # Cần để sử dụng session

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'docx'}

# Tạo thư mục upload nếu chưa có
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Khởi tạo CSDL
def init_db():
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()

    # Tạo bảng users nếu chưa có
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        class TEXT,
        school TEXT
    )''')

    # Tạo bảng dethi nếu chưa có
    c.execute('''CREATE TABLE IF NOT EXISTS dethi (
        id TEXT PRIMARY KEY,
        ten_dethi TEXT,
        so_cau INT,
        dap_an TEXT,
        time INTEGER,
        id_dapan INTEGER CHECK(id_dapan IN (0, 1)),
        action INTEGER CHECK(action IN (0, 1)),
        xt_hs TEXT,
        noidung TEXT,
        time_create TEXT
    )''')

    # tạo bảng baithi nếu chưa tồn tại
    c.execute('''
        CREATE TABLE IF NOT EXISTS baithi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_dethi TEXT NOT NULL,
            id_dethi_hv TEXT NOT NULL,
            id_hocsinh TEXT NOT NULL,
            hoten_hs TEXT,
            lop_hs TEXT,
            truong TEXT,
            ngay_lam TEXT,
            dap_an_lam TEXT,
            diem REAL,
            thoi_gian_lam INTEGER,
            noidung_hv TEXT,
            trang_thai TEXT,
            FOREIGN KEY (id_dethi) REFERENCES dethi(id)
        )
    ''')

    # Tạo bảng chitiet_hv chứa thông tin hoán vị của đề góc và hoán vị, keys hoán vị:
    c.execute('''
    CREATE TABLE IF NOT EXISTS chitiet_hvi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_dethi TEXT NOT NULL,
        id_de_hv TEXT NOT NULL,
        key_qhv TEXT NOT NULL,
        key_ohv TEXT NOT NULL,
        FOREIGN KEY (id_dethi) REFERENCES dethi(id)
    )
''')

    conn.commit()
    conn.close()

# Đọc câu hỏi ban đầu
# questions = read_questions_from_docx("de1.docx","gạhdgajhdg") #demo

# Gán câu hỏi vào app để các Blueprint có thể dùng nếu cần
# app.questions = questions

# Đăng ký blueprint
app.register_blueprint(main_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(users_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(xuli_dethi_bp)
app.register_blueprint(cham_bai_bp)
app.register_blueprint(xuat_excel_bp)
init_db()
if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
