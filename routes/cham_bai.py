from flask import Blueprint, render_template, request, current_app, Response, stream_with_context
from flask import redirect, url_for, flash
from werkzeug.utils import secure_filename
from docx_reader import read_questions_from_docx
from datetime import datetime
import os, sqlite3,json
import random, glob
import string
import json, time
import pandas as pd
from io import BytesIO


cham_bai_bp = Blueprint('cham_bai', __name__)

@cham_bai_bp.route('/cham_lai_dethi/<id_dethi>', methods=['POST'])
def cham_lai_toan_bo_de(id_dethi):
    conn = sqlite3.connect('student_info.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Lấy nội dung đề gốc từ bảng dethi
    c.execute("SELECT noidung FROM dethi WHERE id = ?", (id_dethi,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "❌ Không tìm thấy đề thi.", 404

    try:
        noidung_goc = json.loads(row['noidung'])  # danh sách câu hỏi gốc có answer là chỉ số
    except json.JSONDecodeError:
        conn.close()
        return "❌ Lỗi định dạng JSON trong nội dung đề thi.", 500

    # Lấy toàn bộ bài thi học sinh theo id_dethi
    c.execute("SELECT * FROM baithi WHERE id_dethi = ?", (id_dethi,))
    ds_baithi = c.fetchall()

    so_bai_cham_duoc = 0
    for bai in ds_baithi:
        id_dethi_hv = bai['id_dethi_hv']
        dap_an_lam = bai['dap_an_lam']  # VD: AB*D

        # Bỏ qua nếu chưa làm hoặc dữ liệu không hợp lệ
        if not dap_an_lam or len(dap_an_lam.strip()) == 0:
            continue

        # Lấy key hoán vị từ bảng chitiet_hvi
        c.execute("SELECT key_qhv, key_ohv FROM chitiet_hvi WHERE id_de_hv = ?", (id_dethi_hv,))
        row_keys = c.fetchone()
        if not row_keys:
            continue

        try:
            key_qhv = json.loads(row_keys['key_qhv'])         # ví dụ: [0,2,1,3]
            key_ohv = json.loads(row_keys['key_ohv'])         # ví dụ: [[2,3,1,0], ..., ...]

            so_cau_dung = 0
            for i, ans_hs in enumerate(dap_an_lam):
                if ans_hs == '*':
                    continue  # không tính câu chưa làm

                chi_so_goc = key_qhv[i]                       # chỉ số câu gốc
                ohv = key_ohv[i]                              # hoán vị 4 đáp án của câu i
                chi_so_dung_goc = noidung_goc[chi_so_goc]['answer']  # chỉ số 0-3

                # xác định đáp án đúng sau hoán vị
                vi_tri_dung_sau_hoanvi = ohv.index(chi_so_dung_goc)
                dap_an_dung = 'ABCD'[vi_tri_dung_sau_hoanvi]

                if ans_hs == dap_an_dung:
                    so_cau_dung += 1

            tong_cau = len(key_qhv)
            diem = round((so_cau_dung / tong_cau) * 10, 2)

            # cập nhật điểm và trạng thái
            c.execute('''
                UPDATE baithi SET diem = ?, trang_thai = 'Đã chấm lại'
                WHERE id_dethi_hv = ?
            ''', (diem, id_dethi_hv))
            so_bai_cham_duoc += 1

        except Exception as e:
            print(f"Lỗi khi xử lý bài {id_dethi_hv}: {e}")
            continue
        
    conn.commit()
    conn.close()
    flash(f"Đã chấm lại {so_bai_cham_duoc} bài của mã đề {id_dethi}")
    return redirect(url_for('xuli_dethi.bailam', id_dethi=id_dethi))
