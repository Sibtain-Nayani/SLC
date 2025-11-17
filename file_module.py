import os
import re
import unicodedata
from PyPDF2 import PdfReader
from docx import Document

def clean_text(text):
    """
    Clean and normalize extracted text (fix common mojibake and smart quotes).
    """
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    # Attempt to fix common mojibake by re-encoding
    try:
        text = text.encode("latin1", "ignore").decode("utf-8", "ignore")
    except Exception:
        pass
    # Replace common bad sequences and smart quotes
    replacements = {
        "â": "'",
        "â": "-",
        "â": "-",
        "Â": "",
        "\u2013": "-",
        "\u2014": "-",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Reduce excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_text(file_path):
    """
    Extract text from txt, pdf, docx and return cleaned string.
    """
    ext = os.path.splitext(file_path)[-1].lower()
    raw = ""
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    elif ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
            raw = "\n".join(pages)
        except Exception as e:
            raw = ""
    elif ext == ".docx":
        try:
            doc = Document(file_path)
            paras = [p.text for p in doc.paragraphs if p.text]
            raw = "\n".join(paras)
        except Exception:
            raw = ""
    else:
        # fallback: attempt to read as text
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
        except Exception:
            raw = ""
    return clean_text(raw)
