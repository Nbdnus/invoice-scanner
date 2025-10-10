import re
from datetime import datetime
from typing import Optional, Tuple

# 31.12.2025 oder 1.1.25
DATE_RE = re.compile(r"\b([0-3]?\d\.[01]?\d\.\d{2,4})\b")
# 1.234,56 oder 234,50
AMOUNT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{3})*,\d{2})\b")
CURRENCY_RE = re.compile(r"\b(EUR|€|CHF|USD)\b", re.IGNORECASE)
INVOICE_NO_HINTS = re.compile(r"(rechnungs?nr\.?|rechnung\s*#|invoice\s*no\.?|re\.\s*nr\.)", re.IGNORECASE)
SUPPLIER_CANDIDATE_RE = re.compile(r"^[A-ZÄÖÜẞ][\w&\-\.\s]{3,}$")

def parse_date(text: str):
    m = DATE_RE.search(text)
    if not m:
        return None
    s = m.group(1)
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def parse_amount(text: str) -> Optional[Tuple[float, str]]:
    """Nimmt heuristisch den größten Betrag als Gesamtsumme."""
    matches = AMOUNT_RE.findall(text)
    if not matches:
        return None
    def de_to_float(s: str) -> float:
        return float(s.replace(".", "").replace(",", "."))
    values = [(de_to_float(m), m) for m in matches]
    values.sort(key=lambda x: x[0], reverse=True)
    value_float = values[0][0]
    cur = (CURRENCY_RE.search(text).group(1) if CURRENCY_RE.search(text) else "EUR").upper().replace("€","EUR")
    return value_float, cur

def parse_invoice_number(text: str) -> Optional[str]:
    """Sucht nach Zeilen mit Rechnungsnummer-Hinweis und nimmt den 'komplexesten' Token."""
    lines = text.splitlines()
    for line in lines:
        if INVOICE_NO_HINTS.search(line):
            tokens = re.findall(r"[A-Z0-9\-\/]{3,}", line, re.I)
            if tokens:
                tokens.sort(key=len, reverse=True)
                return tokens[0]
    return None

def guess_supplier(text: str) -> Optional[str]:
    """Heuristik: Lieferant oft im Kopfbereich – erste sinnvollen Zeilen prüfen."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines[:10]:
        if len(ln) > 2 and SUPPLIER_CANDIDATE_RE.match(ln) and not any(k in ln.lower() for k in ["rechnung", "invoice", "kundennummer"]):
            return ln[:255]
    return None

def compute_confidence(parsed: dict) -> float:
    score = 0
    total = 4
    for k in ["supplier_name", "invoice_date", "total_amount", "invoice_number"]:
        if parsed.get(k):
            score += 1
    return round(100.0 * score / total, 2)
