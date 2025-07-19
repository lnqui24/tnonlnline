from flask import Blueprint, render_template, request, current_app
from flask import redirect, url_for, flash
from werkzeug.utils import secure_filename
from docx_reader import read_questions_from_docx
from datetime import datetime
import os, sqlite3,json
import random, glob
import string
main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return redirect(url_for('upload.danh_sach_de_thi'))
