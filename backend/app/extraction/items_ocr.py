from __future__ import annotations
import os
import re
from typing import List, Dict, Any, Optional

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# --- Regex/Heuristiken ---
NUM_RE = re.compile(r"-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?")
CURR_RE = re.compile(r"(€|EUR|USD|GBP)", re.IGNORECASE)
PCT_RE = re.compile(r"(\d{1,2})([.,]\d+)?\s*%")

HEADER_TOKENS = {
    "menge", "anzahl", "qty",
    "einzelpreis", "ep", "stk", "preis",
    "gesamt", "summe", "betrag", "zeilensumme", "zwischensumme",
    "bezeichnung", "beschreibung", "artikel", "position", "leistung"
}

NOISE_TOKENS = {
    "iban", "bic", "ust-id", "ustid", "ust", "steuer", "tax",
    "tel", "telefon", "fax", "mail", "straße", "str.", "road", "gmbh",
    "rechnung", "invoice", "kundennummer", "kunden-nr", "bestellnr", "bestell-nr",
}


def _set_tesseract_cmd_from_env():
    cmd = os.getenv("TESSERACT_CMD")
    if cmd and os.path.exists(cmd):
        pytesseract.pytesseract.tesseract_cmd = cmd


def _normalize_number(s: str) -> Optional[float]:
    if not s:
        return None
    s = CURR_RE.sub("", s)
    s = s.replace(" ", "")
    m = NUM_RE.search(s)
    if not m:
        return None
    num = m.group(0)
    if "," in num and "." in num:
        num = num.replace(".", "").replace(",", ".")
    elif num.count(".") > 1:
        num = num.replace(".", "")
    elif "," in num:
        num = num.replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None


def _render_page_to_image(page: fitz.Page, zoom: float = 3.0) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def _tsv_words(img: Image.Image) -> List[Dict[str, Any]]:
    cfg = "--psm 6"
    data = pytesseract.image_to_data(img, lang="deu+eng", output_type=pytesseract.Output.DICT, config=cfg)
    words = []
    n = len(data["text"])
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1.0
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        words.append({
            "text": txt, "conf": conf,
            "x": int(x), "y": int(y), "w": int(w), "h": int(h),
            "cx": x + w/2.0, "cy": y + h/2.0,
            "right": x + w, "bottom": y + h,
        })
    return words


def _cluster_rows(words: List[Dict[str, Any]], y_tol: int = 7) -> List[List[Dict[str, Any]]]:
    if not words:
        return []
    words = sorted(words, key=lambda w: (w["cy"], w["x"]))
    rows: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    last_cy = None
    for w in words:
        if last_cy is None:
            current = [w]
            last_cy = w["cy"]
            continue
        if abs(w["cy"] - last_cy) <= y_tol:
            current.append(w)
            last_cy = (last_cy + w["cy"]) / 2.0
        else:
            if current:
                rows.append(sorted(current, key=lambda t: t["x"]))
            current = [w]
            last_cy = w["cy"]
    if current:
        rows.append(sorted(current, key=lambda t: t["x"]))
    return rows


def _is_header_row(row: List[Dict[str, Any]]) -> bool:
    text = " ".join((t["text"] or "").lower() for t in row)
    hits = sum(1 for k in HEADER_TOKENS if k in text)
    return hits >= 2


def _is_noise_row(row: List[Dict[str, Any]]) -> bool:
    text = " ".join((t["text"] or "").lower() for t in row)
    return any(k in text for k in NOISE_TOKENS)


def _classify_line(row: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not row:
        return {}

    tokens = []
    for t in row:
        raw = t["text"]
        val = _normalize_number(raw)
        tokens.append({
            "t": t, "text": raw, "x": t["x"],
            "val": val,
            "is_num": (val is not None) and (not PCT_RE.search(raw)),
            "has_curr": bool(CURR_RE.search(raw)),
        })

    nums = [k for k in tokens if k["is_num"]]
    if len(nums) < 2:
        return {}

    # line_total: rechts + ggf. mit Währung, sonst größte rechts
    with_curr = [n for n in nums if n["has_curr"]]
    if with_curr:
        line_total_token = max(with_curr, key=lambda k: (k["x"], k["val"]))
    else:
        line_total_token = max(nums, key=lambda k: (k["x"], k["val"]))
    line_total = line_total_token["val"]

    left_nums = [n for n in nums if n["x"] < line_total_token["x"] and n["val"] and n["val"] > 0]

    unit_price = None
    if left_nums:
        plausible = [n for n in left_nums if n["val"] <= line_total] or left_nums
        unit_price = max(plausible, key=lambda k: k["val"])["val"]

    quantity = None
    qty_candidates = [n for n in left_nums if (unit_price is None or n["val"] != unit_price)]
    if qty_candidates:
        qty_candidates.sort(key=lambda k: (k["x"], k["val"]))
        for c in qty_candidates:
            v = c["val"]
            if v is not None and 0 < v <= 10000:
                quantity = v
                break

    # Beschreibung: Text links von total, der nicht reine Zahl ist
    right_border = line_total_token["x"]
    desc_parts: List[str] = []
    for k in tokens:
        if k["x"] >= right_border:
            continue
        if k["is_num"] and not k["has_curr"]:
            continue
        txt = k["text"].strip()
        if not txt:
            continue
        desc_parts.append(txt)
    description = " ".join(desc_parts).strip() or None

    return {
        "description": description,
        "quantity": quantity,
        "unit": None,
        "unit_price": unit_price,
        "vat_rate": None,
        "vat_amount": None,
        "line_total": line_total,
    }


def _extract_rows(rows: List[List[Dict[str, Any]]], require_header: bool) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    started = not require_header
    for row in rows:
        if _is_noise_row(row):
            continue
        if require_header and not started:
            if _is_header_row(row):
                started = True
            continue
        line = _classify_line(row)
        have = sum(1 for k in ("quantity", "unit_price", "line_total") if line.get(k) is not None)
        if have >= 2 or (line.get("description") and line.get("line_total") is not None):
            line["line_index"] = len(items) + 1
            items.append(line)
    return items


def extract_items_from_pdf(path: str) -> List[Dict[str, Any]]:
    """
    Robuste Positions-Extraktion für GESCANNTE PDFs (OCR), v3:
    - Höherer Render-Zoom (3.0) für klareres OCR.
    - Header-Erkennung (Menge/Einzelpreis/Gesamt...), aber Fallback ohne Header.
    - Rauschen (Adresse/IBAN/USt) wird gefiltert.
    """
    _set_tesseract_cmd_from_env()
    all_items: List[Dict[str, Any]] = []

    with fitz.open(path) as doc:
        for page in doc:
            img = _render_page_to_image(page, zoom=3.0)
            words = _tsv_words(img)
            rows = _cluster_rows(words, y_tol=7)

            # 1) Normal: erst ab Header sammeln
            items = _extract_rows(rows, require_header=True)
            # 2) Fallback: kein Header gefunden → trotzdem versuchen
            if not items:
                items = _extract_rows(rows, require_header=False)

            all_items.extend(items)

    # Filter: Offensichtliche Summen-/MwSt-Zeilen raus
    cleaned: List[Dict[str, Any]] = []
    for it in all_items:
        desc = (it.get("description") or "").lower()
        if any(k in desc for k in ["summe", "gesamt", "rechnungssumme", "mwst", "ust", "netto", "brutto"]):
            continue
        cleaned.append(it)

    return cleaned
