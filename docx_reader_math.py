import os
import re
import uuid
import zipfile
from docx import Document
from flask import flash, redirect, url_for, render_template
from xml.etree import ElementTree as ET
class InvalidDocxFile(Exception): pass
class FileLockedError(Exception): pass
class XMLParseError(Exception): pass

# Thư mục lưu ảnh
IMAGE_FOLDER = 'static/images'
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Namespace
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'
}

# Trích xuất ảnh
def extract_images(docx_path, code):
    image_map = {}
    with zipfile.ZipFile(docx_path) as docx_zip:
        rels_path = 'word/_rels/document.xml.rels'
        if rels_path not in docx_zip.namelist():
            return {}

        rels_root = ET.parse(docx_zip.open(rels_path)).getroot()
        rels = {r.attrib['Id']: r.attrib['Target'] for r in rels_root if 'Id' in r.attrib}

        document = ET.parse(docx_zip.open('word/document.xml')).getroot()
        drawings = document.findall('.//w:drawing', NS)

        cnt_img = 0
        for drawing in drawings:
            cnt_img = cnt_img + 1
            blip = drawing.find('.//a:blip', NS)
            if blip is not None:
                r_id = blip.attrib.get(f'{{{NS["r"]}}}embed')
                if r_id and r_id in rels:
                    image_part = rels[r_id]
                    if image_part.startswith('media/'):
                        img_data = docx_zip.read(f'word/{image_part}')
                        ext = os.path.splitext(image_part)[-1]
                        # name = f"image_{uuid.uuid4().hex[:8]}{ext}"
                        name = f"image_{code}_{cnt_img}{ext}"
                        path = os.path.join(IMAGE_FOLDER, name)
                        with open(path, 'wb') as f:
                            f.write(img_data)
                        image_map[r_id] = f"[static/images/{name}]"
    return image_map

# Lấy text trong công thức
def get_omml_text(el):
    return ''.join(t.text for t in el.iter() if t.tag.endswith('t') and t.text)

# Chuyển OMML thành LaTeX
def omml_to_latex(omml):
    def parse_node(node):
        if node is None: return ""
        tag = node.tag.split('}')[-1]

        if tag == "f":
            num = parse_node(node.find('m:num', NS))
            den = parse_node(node.find('m:den', NS))
            return f"\\frac{{{num}}}{{{den}}}"
        elif tag == "sSup":
            base = parse_node(node.find('m:e', NS))
            sup = parse_node(node.find('m:sup', NS))
            return f"{base}^{{{sup}}}"
        elif tag == "sSub":
            base = parse_node(node.find('m:e', NS))
            sub = parse_node(node.find('m:sub', NS))
            return f"{base}_{{{sub}}}"
        elif tag == "sSubSup":
            base = parse_node(node.find('m:e', NS))
            sub = parse_node(node.find('m:sub', NS))
            sup = parse_node(node.find('m:sup', NS))
            return f"{base}_{{{sub}}}^{{{sup}}}"
        elif tag == "rad":
            deg = parse_node(node.find('m:deg', NS))
            e = parse_node(node.find('m:e', NS))
            return f"\\sqrt[{deg}]{{{e}}}" if deg else f"\\sqrt{{{e}}}"
        elif tag == "nary":
            # Tìm biểu tượng ∫, ∑, ∏ trong naryPr
            chr_node = node.find('m:naryPr/m:chr', NS)
            symbol = chr_node.attrib.get(f'{{{NS["m"]}}}val', '') if chr_node is not None else ''
            sub = parse_node(node.find('m:sub', NS))
            sup = parse_node(node.find('m:sup', NS))
            expr_nodes = node.findall('m:e', NS)
            expr = ' '.join(parse_node(e) for e in expr_nodes)

            # map biểu tượng sang LaTeX
            if symbol == '∑':
                return f"\\sum_{{{sub}}}^{{{sup}}} {expr}"
            elif symbol == '∏':
                return f"\\prod_{{{sub}}}^{{{sup}}} {expr}"
            elif symbol == '∫':
                return f"\\int_{{{sub}}}^{{{sup}}} {expr}"
            else:
                return f"\\int_{{{sub}}}^{{{sup}}} {expr}"

        elif tag == "bar":
            return f"\\overline{{{parse_node(node.find('m:e', NS))}}}"
        elif tag == "box":
            return f"\\boxed{{{parse_node(node.find('m:e', NS))}}}"
        elif tag == "r":
            return get_omml_text(node)
        elif tag == "t":
            return node.text or ""
        else:
            return ''.join(parse_node(child) for child in node)
    latex = parse_node(omml)
    return f"\\({latex}\\)" if latex else ""

# Trích xuất nội dung từ đoạn văn, bao gồm công thức, ảnh, chỉ số mũ
# def extract_text_with_latex(p, image_map):
#     result = []
#     for child in p._element:
#         tag = child.tag.split('}')[-1]
#         if tag == "r":
#             drawing = child.find('.//w:drawing', NS)
#             omath = child.find('.//m:oMath', NS)
#             t_el = child.find('.//w:t', NS)
#             vert = child.find('.//w:vertAlign', NS)
#             if drawing is not None:
#                 blip = drawing.find('.//a:blip', NS)
#                 if blip is not None:
#                     r_id = blip.attrib.get(f'{{{NS["r"]}}}embed')
#                     if r_id in image_map:
#                         result.append(image_map[r_id])
#             elif omath is not None:
#                 result.append(omml_to_latex(omath))
#             elif t_el is not None:
#                 if vert is not None and vert.attrib.get(f'{{{NS["w"]}}}val') == 'superscript':
#                     result.append(f"^{{{t_el.text}}}")
#                 else:
#                     result.append(t_el.text)
#         elif tag == "oMath":
#             result.append(omml_to_latex(child))
#         elif tag == "oMathPara":
#             for om in child.findall('.//m:oMath', NS):
#                 result.append(omml_to_latex(om))
#     return ''.join(result).strip()
# ct mới###################

def extract_text_with_latex(p, image_map):
    result = []

    for child in p._element:
        tag = child.tag.split('}')[-1]
        if tag == "r":
            drawing = child.find('.//w:drawing', NS)
            omath = child.find('.//m:oMath', NS)
            t_el = child.find('.//w:t', NS)
            vert = child.find('.//w:vertAlign', NS)
            if drawing is not None:
                # blip = drawing.find('.//a:blip', NS)

                blip = None
                # Duyệt sâu toàn bộ drawing để tìm blip theo kiểu "hữu cơ"
                for el in drawing.iter():
                    if el.tag.endswith('blip') and f'{{{NS["r"]}}}embed' in el.attrib:
                        blip = el
                        break

                if blip is not None:
                    r_id = blip.attrib.get(f'{{{NS["r"]}}}embed')
                    if r_id in image_map:
                        result.append(image_map[r_id])

            elif omath is not None:
                result.append(omml_to_latex(omath))

            elif t_el is not None:
                text = t_el.text or ""
                if vert is not None:
                    val = vert.attrib.get(f'{{{NS["w"]}}}val')
                    if val == 'superscript':
                        if result:
                            prev = result.pop()
                            # result.append(f"\\{prev}^{{{text}}}")
                            result.append(f"\\({prev}^{{{text}}}\\)")

                        else:
                            result.append(f"^{{{text}}}")
                    elif val == 'subscript':
                        if result:
                            prev = result.pop()
                            # result.append(f"\\{prev}_{{{text}}}")
                            result.append(f"\\({prev}_{{{text}}}\\)")

                        else:
                            result.append(f"_{{{text}}}")
                    else:
                        result.append(text)
                else:
                    result.append(text)

        elif tag == "oMath":
            result.append(omml_to_latex(child))

        elif tag == "oMathPara":
            for om in child.findall('.//m:oMath', NS):
                result.append(omml_to_latex(om))

    return ''.join(result).strip()

# Hàm chính
def read_questions_from_docx(docx_path, code):
    image_map = extract_images(docx_path,code)
    doc = Document(docx_path)
    questions = []
    current_question = []
    options = []
    answer = 0

    for para in doc.paragraphs:
        full_text = extract_text_with_latex(para, image_map)
        if not full_text:
            continue
        if re.match(r"^Câu\s+\d+", full_text, re.IGNORECASE):
            if current_question and len(options) >= 4:
                questions.append({
                    "question": current_question,
                    "options": [op for op in options if len(op)],
                    "answer": answer
                })

            full_text = re.sub(r"^Câu\s*\d+[.:]?", "", full_text)
            full_text = full_text.strip()
            current_question = [full_text]
            options = []
        elif re.match(r"^[A-D]\.", full_text):
            parts = re.split(r"(?=[A-D]\.)", full_text)
            for part in parts:
                if re.match(r"^[A-D]\.", part):
                    options.append(part[2:].strip())                    
        elif len(options) < 4:
            if len(options) == 0:
                current_question.append(full_text)
            else:
                options.append(full_text)
    if current_question and len(options) >= 4:
        print(current_question)
        questions.append({
            "question": current_question,
            "options": [op for op in options if len(op)],
            "answer": answer
        })
    for q in questions:
        q['question'] = "\n".join(q['question'])
    return questions
