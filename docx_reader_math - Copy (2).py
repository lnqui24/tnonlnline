from docx import Document
import os, re, zipfile
import xml.etree.ElementTree as ET
class InvalidDocxFile(Exception): pass
class FileLockedError(Exception): pass
class XMLParseError(Exception): pass

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'
}

def omml_to_latex(node):
    if node is None:
        return ""
    tag = node.tag.split('}')[-1]
    if tag == 'r':
        return ''.join(omml_to_latex(child) for child in node)
    elif tag == 't':
        return node.text
    # elif tag == 'sSup':
    #     base = omml_to_latex(node.find('m:e', NS))
    #     sub = omml_to_latex(node.find('m:sup', NS))
    #     return f"{base}^{{{sub}}}"
    # elif tag == 'sSub':
    #     base = omml_to_latex(node.find('m:e', NS))
    #     sub = omml_to_latex(node.find('m:sub', NS))
    #     return f"{base}_{{{sub}}}"
    if tag == 'sSup':     # mũ
        base = omml_to_latex(node.find('m:e', NS))
        sup  = omml_to_latex(node.find('m:sup', NS))
        return f"{base}^{{{sup}}}"

    if tag == 'sSub':     # chỉ số dưới
        base = omml_to_latex(node.find('m:e', NS))
        sub  = omml_to_latex(node.find('m:sub', NS))
        return f"{base}_{{{sub}}}"

    elif tag == 'nary':
        # chr_node = node.find('m:chr', NS)
        chr_node = node.find('m:naryPr/m:chr', NS)
        symbol = chr_node.attrib.get(f'{{{NS["m"]}}}val', '') if chr_node is not None else ''
        sub = omml_to_latex(node.find('m:sub', NS))
        sup = omml_to_latex(node.find('m:sup', NS))
        expr_nodes = node.findall('m:e', NS)
        expr = ' '.join(omml_to_latex(e) for e in expr_nodes)
        if symbol == '∑':
            return f"\\sum_{{{sub}}}^{{{sup}}} {expr}"
        else:
            return f"\\int_{{{sub}}}^{{{sup}}} {expr}"
    elif tag == 'f':
        num = omml_to_latex(node.find('m:num', NS))
        den = omml_to_latex(node.find('m:den', NS))
        return f"\\frac{{{num}}}{{{den}}}"
    elif tag == 'rad':
        base = omml_to_latex(node.find('m:e', NS))
        deg = node.find('m:deg', NS)
        if deg is not None:
            deg_val = omml_to_latex(deg)
            return f"\\sqrt[{deg_val}]{{{base}}}"
        return f"\\sqrt{{{base}}}"
    else:
        return ''.join(omml_to_latex(child) for child in node)

def extract_equations_from_paragraph(para_element):
    PUNCT_START = (",", ".", ":", ";", "!", "?", ")", "]")
    latex_text = []

    # Xử lý văn bản thường + chỉ số
    for run in para_element.findall('.//w:r', NS):
        t_node = run.find('.//w:t', NS)
        if t_node is not None and t_node.text:
            text = t_node.text
            if (latex_text
                and not latex_text[-1].endswith(" ")
                and not text.startswith((" ",) + PUNCT_START)):
                latex_text.append(" ")
            vert = run.find('.//w:vertAlign', NS)
            if vert is not None:
                align = vert.attrib.get(f'{{{NS["w"]}}}val')
                if align == 'superscript':
                    latex_text.append(f"\\(^{text}\\)")
                elif align == 'subscript':
                    latex_text.append(f"\\(_{text}\\)")
                else:
                    latex_text.append(text)
            else:
                latex_text.append(text)

    # Công thức OMML vẫn bọc nguyên đoạn
    for run in para_element.findall(".//m:oMath", NS):
        latex = omml_to_latex(run)
        if latex:
            latex_text.append(f"\\({latex}\\)")

    return ''.join(latex_text)

def read_questions_from_docx(file_path, code, image_folder="static/images"):
    if not os.path.isfile(file_path):
        raise InvalidDocxFile(f"Không tìm thấy file: {file_path}")
    if not zipfile.is_zipfile(file_path):
        raise InvalidDocxFile("File không đúng định dạng .docx hoặc bị lỗi.")
    try:
        doc = Document(file_path)   
    except KeyError as e:
        raise InvalidDocxFile("Không thể đọc file docx, file có thể bị lỗi hoặc không đúng định dạng!") from e
    questions = []
    current_question = {
        "question": [],
        "options": [],
        "answer": None
    }

    if not os.path.exists(image_folder):
        os.makedirs(image_folder)

    # Đọc XML gốc để lấy cấu trúc sup/sub + equation
    try:
        with zipfile.ZipFile(file_path) as docx:
            with docx.open("word/document.xml") as f:
                tree = ET.parse(f)
                xml_root = tree.getroot()
    except ET.ParseError as e:
        raise XMLParseError("Không thể phân tích cấu trúc XML trong file Word.") from e
    except KeyError:
        raise XMLParseError("Thiếu thành phần word/document.xml trong file docx.")
    
    xml_paragraphs = xml_root.findall('.//w:body/w:p', NS)

    for para, para_xml in zip(doc.paragraphs, xml_paragraphs):
        text = para.text.strip()
        combined = extract_equations_from_paragraph(para_xml)
        if combined:
            if not re.match(r"^[A-D]\.", combined):
                combined = re.sub(r"^Câu\s*\d+[.:]?", "", combined)
                current_question["question"].append(combined.strip())
                pending_option_line = ""
            else:
                pending_option_line += " " + combined.strip()
                #options_found = re.findall(r"[A-D]\.\s*([^A-D]*)", pending_option_line)
                #options_found = re.findall(r"[A-D]\.\s*(.*?)(?=\s+[A-D]\.|$)", pending_option_line)
                # options_found = re.findall(r"[A-D]\.\s*(.*?)(?=\s*[A-D]\.|$)",pending_option_line)
                options_found = re.findall(r"[A-D]\s*\.\s*(.*?)(?=\s*[A-D]\s*\.\s*|$)",pending_option_line)
                if len(options_found) >= 4:
                    current_question["options"].extend([opt.strip() for opt in options_found[:4]])
                    # current_question['options'] = options_found.copy()
                    questions.append(current_question)
                    current_question = {"question": [], "options": [], "answer": None}
                    pending_option_line = ""

        # Xử lý ảnh trong đoạn văn
        for run in para.runs:
            if run.element.xml.find('<w:drawing>') != -1:
                cnt_img = len([f for f in os.listdir(image_folder) if f.startswith(f"image_{code}")]) + 1
                image_data = run._element.xpath('.//a:blip')[0].get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
                )
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
    if not questions:
        raise InvalidDocxFile("Không tìm thấy câu hỏi hợp lệ trong file.")
    return questions    
