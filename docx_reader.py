from docx import Document
import os,random
import re

def read_questions_from_docx(file_path, code, image_folder="static/images"):
    doc = Document(file_path)
    questions = []
    current_question = None

    # Tạo thư mục lưu ảnh nếu chưa có
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)

    current_question = {
        "question": [],  
        "options": [],
        "answer": None
    }
    cnt_img = 0

    for para in doc.paragraphs:
        text = para.text.strip()
       
        if text:
            if not re.match(r"^[A-D]\.", text):
                text = re.sub(r"^Câu\s*\d+[.:]?", "", text).strip()              
                current_question["question"].append(text)
            else:
                text = re.sub(r"^[A-D]\.\s*", "", text, flags=re.MULTILINE)
                current_question["options"].append(text)                        
        
        for run in para.runs:
            if run.element.xml.find('<w:drawing>') != -1:
                cnt_img += 1
                image_data = run._element.xpath('.//a:blip')[0].get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                image_part = doc.part.related_parts[image_data]
                image_path = f"{image_folder}/image_{code}_{cnt_img}.jpg"
                
                with open(image_path, "wb") as img_file:
                    img_file.write(image_part.blob)

                current_question["question"].append("[" + image_path + "]")

        if len(current_question["options"]) == 4:
            questions.append(current_question)
            current_question = {
                "question": [],  
                "options": [],
                "answer": None
            }
    return questions
