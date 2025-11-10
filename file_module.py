import os
import re
import unicodedata
from PyPDF2 import PdfReader
from docx import Document

def clean_text(text):
    """
    Cleans and normalizes text extracted from various file types.
    Fixes bad encodings like 'â€™', 'Â', 'â', etc.
    """
    # Normalize unicode (e.g. smart quotes → normal quotes)
    text = unicodedata.normalize("NFKC", text)

    # Encode/decode to clean up weird bytes (fixes â€™, Â, etc.)
    text = text.encode("latin1", "ignore").decode("utf-8", "ignore")

    # Remove residual bad symbols or control chars
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # keep only basic ASCII
    text = re.sub(r"\s+", " ", text).strip()    # collapse multiple spaces

    # Common replacements
    replacements = {
        "â": "'",
        "â": "-",
        "â": "-",
        "Â": "",
        "â€˜": "'",
        "â€œ": '"',
        "â€": '"',
        "â€¢": "•",
        "â€¦": "...",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    return text


def read_text_from_path(file_path):
    """
    Extracts text from TXT, PDF, or DOCX files and returns cleaned output.
    """
    ext = os.path.splitext(file_path)[-1].lower()
    raw_text = ""

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()

    elif ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"
        except Exception as e:
            raw_text = f"[Error reading PDF: {e}]"

    elif ext == ".docx":
        try:
            doc = Document(file_path)
            raw_text = "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            raw_text = f"[Error reading DOCX: {e}]"

    else:
        raw_text = "[Unsupported file type. Please upload .txt, .pdf, or .docx files.]"

    return clean_text(raw_text)
