from flask import Blueprint, render_template, request, current_app
from flask import redirect, url_for, flash
from werkzeug.utils import secure_filename
from docx_reader_math import (read_questions_from_docx, InvalidDocxFile, FileLockedError, XMLParseError)
from datetime import datetime
import os, sqlite3,json
import random, glob
import string
import json

upload_bp = Blueprint('upload', __name__)

# Tạo thư mục uploads nếu chưa tồn tại
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Hàm kiểm tra đuôi file hợp lệ
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'docx'

# Hàm tạo hậu tố ngẫu nhiên gồm 12 ký tự a-z và 0-9
def generate_random_suffix(length = 6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def update_answers(questions, answer_str):    
    for i, q in enumerate(questions):
        answer_char = answer_str[i].upper()
        index = ord(answer_char) - ord('A')
        q['answer'] = index
    return questions

def add_dethi_to_db(id: str, ten_dethi:str, so_cau:int, dap_an:str, time: int, id_dapan: int,  questions: list, db_path: str = 'student_info.db'):
    time_create = datetime.now().isoformat()
    action = 0
    xt_hs = "Họ tên, Lớp, Trường"
    questions_new = update_answers(questions=questions, answer_str=dap_an)
    noidung = json.dumps(questions_new, ensure_ascii=False)  # giữ Unicode, dấu tiếng Việt
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO dethi (id, ten_dethi, so_cau, dap_an, time, id_dapan, action, xt_hs, noidung, time_create)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (id, ten_dethi, so_cau, dap_an, time, id_dapan, action, xt_hs, noidung, time_create))
    conn.commit()
    conn.close()

@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        
        random_suffix = generate_random_suffix()
        original_name, ext = os.path.splitext(secure_filename(file.filename))
        new_filename = f"{original_name}_{random_suffix}{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)
        file.save(filepath)
        try:
            questions = read_questions_from_docx(filepath,random_suffix)
        except (InvalidDocxFile, FileLockedError, XMLParseError) as e:
            flash(f"Lỗi khi đọc file đề thi: {str(e)}", 'error')
            return redirect(url_for('upload.upload'))
        except Exception as e:
            flash("Đã xảy ra lỗi không xác định!", 'error')
            return redirect(url_for('upload.upload'))
        
        if file and allowed_file(file.filename):
            # original_name, ext = os.path.splitext(secure_filename(file.filename))
            #random_suffix = generate_random_suffix()
            # new_filename = f"{original_name}_{random_suffix}{ext}"
            # filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)
            # file.save(filepath)
            # Đọc câu hỏi từ file đã lưu
            
            # questions = read_questions_from_docx(filepath,random_suffix)

            time = 30 #phut
            id_dapan = 0
            ten_dethi =""
            dap_an = "A" * len(questions)
            add_dethi_to_db(id=random_suffix, ten_dethi=ten_dethi, dap_an=dap_an, so_cau=len(questions), time=time, id_dapan=id_dapan, questions=questions)
            xt_list = ['Họ tên', 'Lớp', 'Trường']
            return render_template('preview.html', questions=questions, id_dethi=random_suffix, dap_an = dap_an, xt_list=xt_list)
    return render_template('upload.html')

@upload_bp.route('/save_dethi', methods=['POST'])
def save_exam_info():
    dap_an1 = ""
    idx = 0
    while True:
        key = f'dap_an_{idx}'
        if key not in request.form:
            break
        dap_an1 += request.form.get(key)
        idx += 1

    id_dethi = request.form.get('id_dethi')
    ten_dethi = request.form.get('ten_dethi', '').strip()
    time = request.form.get('timeLimit', 30)
    id_dapan = 1 if request.form.get('id_dapan') else 0
    time_create = datetime.now().isoformat()

    xt_tt =""
    xt_ht = request.form.get('xt_ht', '')
    xt_lop = request.form.get('xt_lop', '')
    xt_tr = request.form.get('xt_tr', '')
    
    xt_parts = []
    if xt_ht:
        xt_parts.append(xt_ht)
    if xt_lop:
        xt_parts.append(xt_lop)
    if xt_tr:
        xt_parts.append(xt_tr)

    xt_tt = ", ".join(xt_parts)

    try:
        time = int(time)
    except ValueError:
        time = 30

    # Cập nhật vào CSDL
        
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()

    # Bước 1: Lấy questions từ noidung trong CSDL
    conn = sqlite3.connect('student_info.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT noidung FROM dethi WHERE id = ?", (id_dethi,))
    row = c.fetchone()
    if row and row['noidung']:
        try:
            questions = json.loads(row['noidung'])
            for i, ch in enumerate(dap_an1):
                if i < len(questions):
                    index = "ABCD".find(ch.upper())  # Chuyển 'A' → 0, 'B' → 1, ...
                    if 0 <= index <= 3:
                        questions[i]['answer'] = index
            updated_noidung = json.dumps(questions, ensure_ascii=False)
            c.execute('''
                UPDATE dethi
                SET noidung = ?
                WHERE id = ?
            ''', (updated_noidung, id_dethi))

        except json.JSONDecodeError:
            flash("Lỗi khi xử lý nội dung đề thi.", "danger")
    else:
        flash("Không tìm thấy nội dung đề thi.", "danger")

    c.execute('''
        UPDATE dethi
        SET ten_dethi = ?, time = ?, id_dapan = ?, dap_an = ?, xt_hs = ?
        WHERE id = ?
    ''', (ten_dethi, time, id_dapan, dap_an1, xt_tt, id_dethi, ))
    conn.commit()
    conn.close()
    flash('Đã lưu đề thi thành công.', 'success')
    return redirect(url_for('upload.chinh_sua_de', id_dethi=id_dethi))
    # return render_template("success.html", message="Đã lưu đề thi thành công.")

@upload_bp.route('/quanli_dethi', methods=['GET'])
def danh_sach_de_thi():
    search_id = request.args.get('search_id', '').strip()

    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()

    if search_id:
        c.execute('''
            SELECT d.id, d.ten_dethi, d.so_cau, d.dap_an, d.time, d.id_dapan, d.action, d.xt_hs, d.time_create,
                   COUNT(b.id_hocsinh) as sl_hs
            FROM dethi d
            LEFT JOIN baithi b ON d.id = b.id_dethi
            WHERE d.id LIKE ?
            GROUP BY d.id
            ORDER BY d.time_create DESC      
        ''', (f'%{search_id}%',))
    else:
        c.execute('''
            SELECT d.id, d.ten_dethi, d.so_cau, d.dap_an, d.time, d.id_dapan, d.action, d.xt_hs, d.time_create,
                   COUNT(b.id_hocsinh) as sl_hs
            FROM dethi d
            LEFT JOIN baithi b ON d.id = b.id_dethi
            GROUP BY d.id
            ORDER BY d.time_create DESC
        ''')

        # 
    rows = c.fetchall()
    conn.close()
    return render_template('quanli_dethi.html', dethi_list=rows)

@upload_bp.route('/de/<id_dethi>', methods=['GET', 'POST'])
def chinh_sua_de(id_dethi):
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    time_create = datetime.now().isoformat()

    if request.method == 'POST':
        ten_dethi = request.form.get('ten_dethi', '')
        xt_tt =""
        xt_ht = request.form.get('xt_ht', '')
        xt_lop = request.form.get('xt_lop', '')
        xt_tr = request.form.get('xt_tr', '')
        time = request.form.get('timeLimit', '30')
        id_dapan = 1 if request.form.get('id_dapan') == 'on' else 0

        # try:
        #     time = int(time)
        # except ValueError:
        #     time = 30

        xt_parts = []
        if xt_ht:
            xt_parts.append(xt_ht)
        if xt_lop:
            xt_parts.append(xt_lop)
        if xt_tr:
            xt_parts.append(xt_tr)

        xt_tt = ", ".join(xt_parts)

        # Cập nhật thông tin đề thi trong CSDL
        c.execute('''
            UPDATE dethi
            SET ten_dethi = ?, time = ?, id_dapan = ?, xt_hs = ?
            WHERE id = ?
        ''', (ten_dethi, time, id_dapan,  xt_tt, id_dethi))
        conn.commit()

    # Truy vấn lại thông tin đề thi để hiển thị
    c.execute('SELECT ten_dethi, time, id_dapan, noidung, dap_an, xt_hs FROM dethi WHERE id = ?', (id_dethi,))
    row = c.fetchone()
    conn.close()

    if row:
        ten_dethi, time, id_dapan, noidung, dap_an, xt_hs = row
        try:
            questions = json.loads(noidung)
        except json.JSONDecodeError:
            return "Lỗi đọc dữ liệu đề thi.", 500
        xt_list = [item.strip() for item in xt_hs.split(',')] if xt_hs else []
        return render_template(
            'preview.html',
            questions=questions,
            id_dethi=id_dethi,
            ten_dethi=ten_dethi,
            timeLimit=time,
            id_dapan=id_dapan,
            dap_an = dap_an,
            xt_list = xt_list
        )
    else:
        return f"Không tìm thấy đề thi có mã: {id_dethi}", 404
    
@upload_bp.route('/xoa_de/<id_dethi>', methods=['GET'])
def xoa_de(id_dethi):
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    c.execute('DELETE FROM dethi WHERE id = ?', (id_dethi,))
    conn.commit()
    conn.execute('VACUUM')
    conn.close()
    # Xoa hình ảnh của đề
    image_folder = os.path.join('static', 'images')
    pattern = os.path.join(image_folder, f'image_{id_dethi}_*.jpg')
    for image_path in glob.glob(pattern):
        try:
            os.remove(image_path)
        except Exception as e:
            print(f"Không thể xoá ảnh {image_path}: {e}")
    # return render_template("success.html", message=f"Đã xoá đề thi có mã: {id_dethi}")
    flash(f'Đã xoá đề thi có mã: {id_dethi}', 'success')
    return redirect(url_for('upload.danh_sach_de_thi'))

@upload_bp.route('/khoa_mo_de/<id_dethi>')
def toggle_khoa_de(id_dethi):
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()

    c.execute('SELECT action FROM dethi WHERE id = ?', (id_dethi,))
    row = c.fetchone()

    if row:
        new_action = 0 if row[0] == 1 else 1  # Đảo trạng thái
        c.execute('UPDATE dethi SET action = ? WHERE id = ?', (new_action, id_dethi))
        conn.commit()
        flash(f'Đã {"mở khóa" if new_action == 0 else "khóa"} đề thi {id_dethi}.', 'success')
    else:
        flash('Không tìm thấy đề thi.', 'error')

    conn.close()
    return redirect(url_for('upload.danh_sach_de_thi'))

