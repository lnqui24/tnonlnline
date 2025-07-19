from flask import Blueprint, Response, flash, redirect, url_for, render_template, request
from docx_reader_math import read_questions_from_docx
import sqlite3, re
import pandas as pd
from io import BytesIO
import zipfile
from lxml import etree
import os

xuat_excel_bp = Blueprint('xuat_excel', __name__)

@xuat_excel_bp.route('/xuat_excel_baithi/<id_dethi>')
def xuat_excel_baithi(id_dethi):
    # Kết nối CSDL
    conn = sqlite3.connect('student_info.db')
    df = pd.read_sql_query("SELECT * FROM baithi WHERE id_dethi = ?", conn, params=(id_dethi,))
    conn.close()

    if 'id' in df.columns:
        df.drop(columns=['id'], inplace=True)

    df.insert(0, 'STT', range(1, len(df) + 1))  # Thêm cột STT từ 1

    df.rename(columns={
        'id': 'STT',
        'id_dethi': 'Mã đề gốc',
        'id_dethi_hv': 'Mã đề hoán vị',
        'id_hocsinh': 'Mã học sinh',
        'hoten_hs': 'Họ tên học sinh',
        'lop_hs': 'Lớp',
        'truong': 'Trường',
        'ngay_lam': 'Ngày làm bài',
        'dap_an_lam': 'Đáp án đã chọn',
        'diem': 'Điểm',
        'thoi_gian_lam': 'Thời gian làm (phút)',
        'noidung_hv': 'Nội dung đề',
        'trang_thai': 'Trạng thái'
    }, inplace=True)

    # Ghi dữ liệu vào Excel trong bộ nhớ
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='BaiThi')

    output.seek(0)
    flash(f"Đã xuất excel thành công!")
    # Trả về file Excel dưới dạng download
    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            "Content-Disposition": "attachment; filename=baithi.xlsx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
    )

# Test

@xuat_excel_bp.route("/test", methods=["GET"])
def test():
    questions = read_questions_from_docx("de_test.docx","001")
    return render_template('test.html', questions=questions)
