from typing import List
import os

import pdfplumber

# Fallback: PyPDF (manchmal erkennt es Text besser als pdfplumber)
def _pypdf_text(path: str) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""
    parts: List[str] = []
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            txt = page.extract_text() or ""
            parts.append(txt)
    except Exception:
        return ""
    return "\n".join(parts).strip()

# OCR mit PyMuPDF (fitz) + Tesseract
def _ocr_text(path: str) -> str:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image
    # optional: tesseract.exe Pfad aus .env übernehmen
    tcmd = os.getenv("TESSERACT_CMD")
    if tcmd and os.path.exists(tcmd):
        pytesseract.pytesseract.tesseract_cmd = tcmd

    parts: List[str] = []
    # Rendering-Qualität: zoom ~2.0 (ca. 144 dpi) ist ein guter Start
    zoom = 2.0
    try:
        with fitz.open(path) as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                # deutsch + englisch ist oft sinnvoll
                txt = pytesseract.image_to_string(img, lang="deu+eng", config="--psm 6")
                parts.append(txt or "")
    except Exception:
        return ""
    return "\n".join(parts).strip()

def extract_text_from_pdf(path: str) -> str:
    """
    Pipeline:
      1) pdfplumber Text
      2) pypdf Text
      3) OCR (PyMuPDF + Tesseract)
    """
    # 1) pdfplumber
    try:
        pl_parts: List[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                pl_parts.append(txt)
        txt = "\n".join(pl_parts).strip()
        if txt:
            return txt
    except Exception:
        pass

    # 2) pypdf
    txt = _pypdf_text(path)
    if txt:
        return txt

    # 3) OCR
    txt = _ocr_text(path)
    return txt or ""
