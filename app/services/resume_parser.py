import fitz  # pymupdf

def parse_resume(file_path: str):
    text = ""
    doc = fitz.open(file_path)

    for page in doc:
        text += page.get_text()

    return text
