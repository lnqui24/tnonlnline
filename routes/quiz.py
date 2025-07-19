from flask import Blueprint, render_template, request, current_app
import sqlite3

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route("/quiz")
def quiz():
    # questions_new = shuffle_questions_and_answers(current_app.questions.copy())
    return render_template("xac_nhan.html")

# @quiz_bp.route("/result", methods=["POST"])
# def result():
#     score = 0
#     user_answers = request.form
#     for i, question in enumerate(current_app.questions):
#         if user_answers.get(f"c{i}") == question["answer"]:
#             score += 1
#     return render_template("result.html", score=score, total=len(current_app.questions))

# @quiz_bp.route("/submit_info", methods=["POST"])
# def submit_info():
#     name = request.form['name']
#     school = request.form['school']
#     class_name = request.form['class']
#     conn = sqlite3.connect('student_info.db')
#     c = conn.cursor()
#     c.execute("INSERT INTO users (name, class, school) VALUES (?, ?, ?)", (name, class_name, school))
#     conn.commit()
#     conn.close()
#     questions_new = shuffle_questions_and_answers(current_app.questions.copy())
#     return render_template("quiz.html", questions=questions_new, users=name, lop=class_name)

# def shuffle_questions_and_answers(questions):
#     import random
#     for q in questions:
#         random.shuffle(q["options"])
#     random.shuffle(questions)
#     return questions
