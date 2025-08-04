from flask import Blueprint, render_template, request, current_app
from flask import redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from docx_reader import read_questions_from_docx
from datetime import datetime
import os, sqlite3,json
import random, glob
import string
import sqlite3
from datetime import datetime
import json
from functions import login_required

xuli_dethi_bp = Blueprint('xuli_dethi', __name__)

def gen_key(n: int):
    tmp_shff = list(range(n))
    random.shuffle(tmp_shff)
    return tmp_shff

def shuffle_options(question_dict, option_key):
    options = question_dict['options']
    correct_index = question_dict['answer']

    # Sinh thứ tự hoán đổi cho 4 đáp án
    #option_key = gen_key(len(options))

    # Hoán đổi options
    shuffled_options = [options[i] for i in option_key]

    # Tìm vị trí mới của đáp án đúng
    new_answer = option_key.index(correct_index)

    # Trả lại dict mới đã shuffle options và cập nhật answer
    return {
        'question': question_dict['question'],
        'options': shuffled_options,
        'answer': new_answer
    }
def shuffle_questions(questions, key_item, option_key_list):
    # Shuffle danh sách câu hỏi
    #key_item = gen_key(len(questions))
    shuffled_questions = [questions[i] for i in key_item]

    # Với mỗi câu hỏi, shuffle options và cập nhật answer
    # final_questions = [shuffle_options(q,option_key) for q in shuffled_questions]
    final_questions = [ shuffle_options(question, option_key) for question, option_key in zip(shuffled_questions, option_key_list)]
    return final_questions

def strip_answers(questions):
    return [
        {
            'question': q['question'],
            'options': q['options']
        }
        for q in questions
    ]

def generate_random_suffix(length = 6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@xuli_dethi_bp.route('/xuli_dethi')
@login_required
def xuli_dethi():
    return render_template("xuli_dethi.html", message="Đã lưu đề thi thành công.")

def update_answers(questions, answer_str):    
    for i, q in enumerate(questions):
        answer_char = answer_str[i].upper()
        index = ord(answer_char) - ord('A')
        if 0 <= index < len(q['options']):
            q['answer'] = index
    return questions

@xuli_dethi_bp.route('/bailam/<id_dethi>')
@login_required
def bailam(id_dethi):
    username = session.get('username',"Ẩn danh")
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()

    # Lấy số học sinh tham gia (đếm học sinh distinct trong baithi)
    c.execute('SELECT COUNT(DISTINCT id_dethi_hv) FROM baithi WHERE id_dethi = ?', (id_dethi,))
    so_hs = c.fetchone()[0]

    c.execute('SELECT COUNT(DISTINCT id_dethi_hv) FROM baithi WHERE id_dethi = ? AND diem is NULL' , (id_dethi,))
    so_hs_chuanop = c.fetchone()[0]

    c.execute('SELECT ten_dethi FROM dethi WHERE id = ?', (id_dethi,))
    ten_dethi = c.fetchone()[0]
    if ten_dethi == "":
        ten_dethi = "(Chưa nhập)"

    # Lấy chi tiết bài làm: id_hocsinh, điểm, thời gian làm, ngày làm, nội dung bài làm
    c.execute('SELECT id_hocsinh, id_dethi_hv, diem, thoi_gian_lam, dap_an_lam, ngay_lam, noidung_hv, hoten_hs, lop_hs, truong, trang_thai FROM baithi WHERE id_dethi = ?', (id_dethi,))
    ket_qua = c.fetchall()
    conn.close()

    return render_template(
        'bailam.html', id_dethi=id_dethi, so_hs=so_hs, 
        so_hs_chuanop = so_hs_chuanop,
        ket_qua=ket_qua, ten_dethi=ten_dethi, username=username)

@xuli_dethi_bp.route('/lam_bai', methods=['GET', 'POST'])
def lam_bai():
    if request.method == 'POST':
        ma_dethi = request.form.get('ma_dethi', '').strip()

        if not ma_dethi:
            flash("Vui lòng nhập mã đề.")
            return redirect(url_for('xuli_dethi.lam_bai'))

        conn = sqlite3.connect('student_info.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM dethi WHERE id = ?", (ma_dethi,))
        dethi = c.fetchone()
        conn.close()

        if not dethi:
            flash("Mã đề thi không tồn tại. Vui lòng kiểm tra lại.")
            return redirect(url_for('xuli_dethi.lam_bai'))

        if dethi['action'] == 1:
            flash("Đề thi đang bị khóa, vui lòng liên hệ giáo viên.")
            return redirect(url_for('xuli_dethi.lam_bai'))

        # Lưu tạm đề thi trong session (hoặc redirect với id)
        session['id_dethi'] = dethi['id']
        return redirect(url_for('xuli_dethi.xac_nhan_chitiet'))

    return render_template('xac_nhan.html')

@xuli_dethi_bp.route('/xac_nhan_chitiet')
def xac_nhan_chitiet():
    id_dethi = session.pop('id_dethi', None)
    conn = sqlite3.connect('student_info.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
            SELECT * FROM dethi WHERE id = ?
        ''', ( id_dethi,))
    dethi = c.fetchone()
    conn.close()
    
    if not id_dethi:
        return redirect(url_for('xuli_dethi.lam_bai'))
    xt_list = [x.strip() for x in dethi['xt_hs'].split(',')] if dethi['xt_hs'] else []
    return render_template('xac_nhan_chitiet.html', dethi=dethi, xt_list=xt_list)

@xuli_dethi_bp.route('/thi', methods=['POST'])
def thi():
    id_dethi = request.form.get('id_dethi')
    hoten = request.form.get('ho_ten', '').title()
    lop = request.form.get('lop', '').upper()
    truong = request.form.get('truong', '').upper()

    # Lấy đề thi từ database
    conn = sqlite3.connect('student_info.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM dethi WHERE id = ?", (id_dethi,))
    dethi = c.fetchone()


    if not dethi:
        flash("Không tìm thấy đề thi.")
        return redirect(url_for('xuli_dethi.lam_bai'))

    if dethi['action'] == 1:
        flash("Đề thi đang bị khóa.")
        return redirect(url_for('xuli_dethi.lam_bai'))

    try:
        questions = json.loads(dethi['noidung'])
    except json.JSONDecodeError:
        return "Lỗi nội dung đề thi.", 500

    id = id_dethi
    id_dethi_hv = id_dethi + "_" + generate_random_suffix()
    noidung_hv = dethi['noidung']
    key_qhv = gen_key(len(questions)) # Tạo key cho câu hỏi
    # key_ohv = gen_key(4) #Tạo key cho đáp án
    key_ohv_list = [gen_key(4) for i in range(len(questions))] # Tạo danh sách đáp án cho tưng câu.

    ngay_lam = datetime.now().strftime("%d/%m/%Y lúc %#H:%M:%S")
    id_hocsinh =""
    dap_an = ""
    dap_an_lam =""


    questions_sh_ans = shuffle_questions(questions,key_qhv, key_ohv_list)
    questions_sh = strip_answers(questions_sh_ans)
    noidung_hv = json.dumps(questions_sh_ans, ensure_ascii=False)

    key_qhv_str = json.dumps(key_qhv, ensure_ascii=False)
    key_ohv_str = json.dumps(key_ohv_list, ensure_ascii=False)
    c.execute(''' INSERT INTO chitiet_hvi (id_dethi, id_de_hv, key_qhv, key_ohv)
              VALUES (?, ?, ?, ?)''', (id_dethi, id_dethi_hv, key_qhv_str, key_ohv_str))

    c.execute('''
        INSERT INTO baithi (id_dethi, id_dethi_hv, id_hocsinh, hoten_hs, lop_hs, truong, ngay_lam, dap_an_lam,
              noidung_hv,trang_thai)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (id, id_dethi_hv, id_hocsinh, hoten, lop, truong, ngay_lam, dap_an_lam, noidung_hv,"Chưa nộp"))
    conn.commit()
    conn.close()

    return render_template(
        'quiz.html', 
        dethi=dethi,
        id_dethi_hv = id_dethi_hv,
        questions=questions_sh,
        hoten=hoten,
        lop=lop,
        truong=truong,
        time = dethi['time']
    )

@xuli_dethi_bp.route('/xoa_bai_lam', methods=['POST'])
@login_required
def xoa_bai_lam():
    id_dethi_hv = request.form.get('id_dethi_hv')
    id_dethi = request.form.get('id_dethi')

    conn = sqlite3.connect('student_info.db')  # Cùng DB như khi lưu
    c = conn.cursor()
    c.execute("DELETE FROM baithi WHERE id_dethi_hv = ?", (id_dethi_hv,))
    conn.commit()
    conn.execute('VACUUM')
    conn.close()

    flash('Đã xoá bài làm thành công.')
    return redirect(url_for('xuli_dethi.bailam', id_dethi=id_dethi))

@xuli_dethi_bp.route('/nopbai', methods=['POST'])
def nopbai():
    # Xử lý dữ liệu nộp bài nếu cần
    # Ví dụ: lưu điểm, đáp án, thời gian làm...

    # Xóa session sau khi nộp bài
    session.pop('current_quiz', None)
    session.pop('dethi_info', None)
    session.pop('student_info', None)

    id_dethi_hv = request.form.get("id_dethi_hv")
    # Lấy số câu hỏi từ đề gốc (hoặc bạn truyền kèm vào form)
    conn = sqlite3.connect('student_info.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM baithi WHERE id_dethi_hv = ?", (id_dethi_hv,))
    baithi = c.fetchone()

    if not baithi:
        return "Không tìm thấy bài thi.", 404
     # Tính thời gian làm bài
    try:
        ngay_lam_str = baithi['ngay_lam']  # VD: "14/06/2025 lúc 10:33:21"
        ngay_lam = datetime.strptime(ngay_lam_str.replace(" lúc ", " "), "%d/%m/%Y %H:%M:%S")
        tmp =(datetime.now() - ngay_lam).total_seconds()
        minutes = int(tmp // 60)
        seconds = int(tmp % 60)
        thoi_gian_lam = f"{minutes}:{seconds:02d}"  # Ví dụ: 2:05
    except Exception:
        thoi_gian_lam = None

    # Lấy nội dung đề hoán vị (gồm cả đáp án)
    try:
        questions_with_answers = json.loads(baithi['noidung_hv'])
    except json.JSONDecodeError:
        return "Lỗi dữ liệu đề thi học viên.", 500

    # Xử lý đáp án học sinh gửi
    answers_hs = []
    total_correct = 0
    ans_hs = ""

    for i, q in enumerate(questions_with_answers):
        dap_an_dung = q['answer']
        dap_an_hs = request.form.get(f'dap_an_{i}', '')
        if dap_an_hs == "": dap_an_hs = "*"
        ans_hs += dap_an_hs
        answers_hs.append(dap_an_hs)

        # Đổi đáp án đúng (index) sang A/B/C/D
        if dap_an_hs == "ABCD"[dap_an_dung]:
            total_correct += 1

    # Tính điểm (ví dụ: mỗi câu 1 điểm)
    diem = round(10 * total_correct / len(questions_with_answers), 1)

    # # Lưu lại vào bảng baithi
    # dap_an_lam_json = json.dumps(answers_hs)

    c.execute('''
        UPDATE baithi
        SET dap_an_lam = ?, diem = ?, thoi_gian_lam = ?, trang_thai = ?
        WHERE id_dethi_hv = ?
        ''', (ans_hs, diem, thoi_gian_lam,
        'Đã nộp bài', id_dethi_hv
    ))
    conn.commit()
    conn.close()
    # Hiển thị trang thông báo
    return render_template('nopbai.html')

@xuli_dethi_bp.route("/api/baithi/<id_dethi>")
def api_lay_baithi(id_dethi):
    conn = sqlite3.connect('student_info.db')
    c = conn.cursor()
    c.execute("""
        SELECT id_hocsinh, id_dethi_hv, diem, thoi_gian_lam, dap_an_lam, ngay_lam, hoten_hs, lop_hs, truong, trang_thai
        FROM baithi
        WHERE id_dethi = ?
    """, (id_dethi,))
    ket_qua = c.fetchall()
    # Convert to list of dicts
    data = [
        {
            "id_hocsinh": row[0],
            "id_dethi_hv": row[1],
            "diem": row[2],
            "thoi_gian_lam": row[3],
            "dap_an_lam": row[4],
            "ngay_lam": row[5],
            "hoten": row[6],
            "lop": row[7],
            "truong": row[8],
            "trang_thai": row[9]
        }
        for row in ket_qua
    ]
    return jsonify(data)

@xuli_dethi_bp.route('/xem_baithi/<id_dethi_hv>')
@login_required
def xem_baithi(id_dethi_hv):
    conn = sqlite3.connect('student_info.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Lấy bài thi
    c.execute("SELECT * FROM baithi WHERE id_dethi_hv = ?", (id_dethi_hv,))
    baithi = c.fetchone()

    if not baithi:
        conn.close()
        return "Không tìm thấy bài thi.", 404

    id_dethi = baithi['id_dethi']
    dap_an_hs = baithi['dap_an_lam'] or ""

    # Lấy đề gốc từ bảng dethi
    c.execute("SELECT * FROM dethi WHERE id = ?", (id_dethi,))
    dethi = c.fetchone()
    if not dethi:
        conn.close()
        return "Không tìm thấy đề gốc.", 404

    try:
        noidung_goc = json.loads(dethi['noidung'])  # danh sách câu hỏi gốc
    except Exception as e:
        conn.close()
        return f"Lỗi khi đọc đề gốc: {e}", 500

    # Lấy key hoán vị từ chitiet_hvi
    c.execute("SELECT key_qhv, key_ohv FROM chitiet_hvi WHERE id_de_hv = ?", (id_dethi_hv,))
    chitiethv = c.fetchone()
    conn.close()

    if not chitiethv:
        return "Không tìm thấy thông tin hoán vị.", 404

    try:
        key_qhv = json.loads(chitiethv['key_qhv'])
        key_ohv = json.loads(chitiethv['key_ohv'])  # danh sách hoán vị 4 đáp án cho từng câu
    except Exception as e:
        return f"Lỗi đọc key hoán vị: {e}", 500

    # Tạo lại danh sách câu hỏi như học sinh đã thấy
    questions_hv = []
    for i, idx_q in enumerate(key_qhv):
        cau_goc = noidung_goc[idx_q]
        options = cau_goc['options']
        shuffled_options = [options[j] for j in key_ohv[i]]
        answer_index = key_ohv[i].index(cau_goc['answer'])  # vị trí mới sau hoán vị

        questions_hv.append({
            'question': cau_goc['question'],
            'options': shuffled_options,
            'answer': answer_index,
        })

    # Gắn đáp án học sinh
    for i, q in enumerate(questions_hv):
        q['hs_chon'] = dap_an_hs[i] if i < len(dap_an_hs) else "*"

    # Tính số câu đúng / sai
    so_cau_dung = 0
    so_cau_sai = 0
    for q in questions_hv:
        hs_chon = q.get('hs_chon')
        dapan_dung = "ABCD"[q['answer']]
        if hs_chon != "*":
            if hs_chon == dapan_dung:
                so_cau_dung += 1
            else:
                so_cau_sai += 1

    return render_template(
        'xem_baithi.html',
        id_dethi_hv=id_dethi_hv,
        questions=questions_hv,
        baithi=baithi,
        so_cau_dung=so_cau_dung,
        so_cau_sai=so_cau_sai
    )

