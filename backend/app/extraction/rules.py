import re
from datetime import datetime
from typing import Optional, Tuple, Dict, List

# --------- Pre-Cleaning (hilft bei OCR) ---------
GER_MONTHS = {
    "januar": 1, "jan": 1,
    "februar": 2, "feb": 2,
    "märz": 3, "maerz": 3, "mrz": 3, "marz": 3,
    "april": 4, "apr": 4,
    "mai": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}

SUPPLIER_KEYWORDS = [
    "gmbh", "ug", "kg", "ag", "gbr", "e.k.", "ek", "ohg", "ug (haftungsbeschränkt)"
]

INVOICE_HINTS = [
    "rechnungsnummer", "rechnungs-nr", "rechnungsnr", "rnr", "beleg-nr", "belegnr",
    "invoice no", "invoice#", "invoice number", "rechnung #", "rechnung nr", "rechnung-nr"
]

TOTAL_HINTS = [
    "rechnungsbetrag", "gesamtbetrag", "bruttosumme", "gesamtsumme",
    "summe", "gesamt", "total", "amount due"
]

CURRENCY_MAP = {"€": "EUR", "eur": "EUR", "euro": "EUR", "usd": "USD", "$": "USD", "chf": "CHF"}


def normalize_text(text: str) -> str:
    """
    Sanftes Cleaning für OCR:
    - Unicode-Normalisierung (nur minimal hier)
    - Whitespaces vereinheitlichen
    - häufige OCR-Fehler rund um € und Punkte/Kommas nicht zu aggressiv anfassen
    """
    if not text:
        return ""
    # Normalize whitespace
    t = re.sub(r"\r", "\n", text)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s+\n", "\n\n", t)
    return t.strip()


# --------- Datum ---------
DATE_DOT = re.compile(r"\b([0-3]?\d)\.([01]?\d)\.(\d{2,4})\b")              # 31.01.2025 / 1.1.25
DATE_DASH = re.compile(r"\b([0-3]?\d)-([01]?\d)-(\d{2,4})\b")               # 31-01-2025
DATE_ISO  = re.compile(r"\b(\d{4})-([01]?\d)-([0-3]?\d)\b")                 # 2025-01-31
DATE_WORD = re.compile(
    r"\b([0-3]?\d)\.\s*([A-Za-zÄÖÜäöüß\.]+)\s+(\d{4})\b"                   # 31. Januar 2025
)

def parse_date(text: str) -> Optional[datetime.date]:
    t = normalize_text(text)

    # 1) 31.01.2025 / 31-01-2025
    m = DATE_DOT.search(t)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(_four_year(m.group(3)))
        return _safe_date(d, mth, y)

    m = DATE_DASH.search(t)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(_four_year(m.group(3)))
        return _safe_date(d, mth, y)

    # 2) 2025-01-31
    m = DATE_ISO.search(t)
    if m:
        y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _safe_date(d, mth, y)

    # 3) 31. Januar 2025
    m = DATE_WORD.search(t.lower())
    if m:
        d = int(m.group(1))
        month_name = m.group(2).replace(".", "")
        y = int(m.group(3))
        mth = GER_MONTHS.get(month_name, None)
        if mth:
            return _safe_date(d, mth, y)

    return None

def _four_year(y: str) -> int:
    return int(y) + 2000 if len(y) == 2 and int(y) < 50 else (int(y) + 1900 if len(y) == 2 else int(y))

def _safe_date(d: int, m: int, y: int):
    try:
        return datetime(year=y, month=m, day=d).date()
    except ValueError:
        return None


# --------- Betrag & Währung ---------
AMOUNT_DE = r"\d{1,3}(?:\.\d{3})*,\d{2}"   # 1.234,56   123,45
AMOUNT_INT = r"\d+\.\d{2}"                 # 1234.56    (falls OCR englisch formatiert)

AMOUNT_RE = re.compile(fr"({AMOUNT_DE}|{AMOUNT_INT})")
CURRENCY_RE = re.compile(r"\b(EUR|EURO|€|USD|\$|CHF)\b", re.IGNORECASE)

def _de_to_float(s: str) -> float:
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    return float(s)

def parse_amount(text: str) -> Optional[Tuple[float, str]]:
    """
    Heuristik:
    1) Suche nach Zeilen mit TOTAL_HINTS und nimm dort den größten Betrag.
    2) Falls nichts: wähle global den größten Betrag.
    """
    t = normalize_text(text)
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]

    # 1) in "Total"-Zeilen schauen
    total_candidates: List[Tuple[float, str]] = []
    for ln in lines:
        if any(h in ln.lower() for h in TOTAL_HINTS):
            for m in AMOUNT_RE.findall(ln):
                try:
                    total_candidates.append((_de_to_float(m), m))
                except Exception:
                    pass
    if total_candidates:
        total_candidates.sort(key=lambda x: x[0], reverse=True)
        value = total_candidates[0][0]
        cur = _find_currency(t)
        return value, cur

    # 2) global größter Betrag
    all_amounts = []
    for m in AMOUNT_RE.findall(t):
        try:
            all_amounts.append((_de_to_float(m), m))
        except Exception:
            pass
    if all_amounts:
        all_amounts.sort(key=lambda x: x[0], reverse=True)
        value = all_amounts[0][0]
        cur = _find_currency(t)
        return value, cur

    return None

def _find_currency(text: str) -> str:
    m = CURRENCY_RE.search(text)
    if not m:
        return "EUR"
    token = m.group(0).lower()
    return CURRENCY_MAP.get(token, "EUR")


# --------- Rechnungsnummer ---------
def parse_invoice_number(text: str) -> Optional[str]:
    t = normalize_text(text).lower()
    lines = [ln for ln in t.splitlines() if ln.strip()]

    # 1) in Hinweislini(en) suchen
    for ln in lines:
        if any(h in ln for h in INVOICE_HINTS):
            tokens = re.findall(r"[a-z0-9][a-z0-9\-\/]{2,}", ln, re.IGNORECASE)
            # Filtere offensichtliche Wörter raus
            tokens = [tok for tok in tokens if not any(w in tok for w in ["rechnung", "invoice", "nummer", "nr"])]
            if tokens:
                tokens.sort(key=len, reverse=True)
                return tokens[0][:100]

    # 2) Fallback: alphanumerische Muster mit Bindestrich / Slash
    m = re.search(r"\b([A-Z0-9]{3,}[\/\-][A-Z0-9\-]{2,})\b", text, re.IGNORECASE)
    if m:
        return m.group(1)[:100]
    return None


# --------- Lieferant ---------
def guess_supplier(text: str) -> Optional[str]:
    """
    Heuristik:
    - prüfe die ersten ~12 Zeilen
    - Zeilen mit Firmenendungen (GmbH/UG/KG/AG/…) bevorzugen
    - keine Zeilen mit 'Rechnung', 'Invoice', 'Kundennummer' etc.
    """
    t = normalize_text(text)
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    head = lines[:12]

    # 1) Zeilen mit typischen Firmenendungen
    for ln in head:
        low = ln.lower()
        if any(k in low for k in SUPPLIER_KEYWORDS):
            if not any(bad in low for bad in ["rechnung", "invoice", "kundennummer", "customer"]):
                return ln[:255]

    # 2) Fallback: erste „titelartige“ Zeile (Großbuchstaben am Anfang, nicht zu kurz)
    for ln in head:
        if re.match(r"^[A-ZÄÖÜẞ][\w&\-\.\s]{3,}$", ln) and not any(bad in ln.lower() for bad in ["rechnung", "invoice", "kundennummer"]):
            return ln[:255]
    return None


# --------- Confidence ---------
def compute_confidence(parsed: Dict) -> float:
    score = 0
    total = 4
    for k in ["supplier_name", "invoice_date", "total_amount", "invoice_number"]:
        if parsed.get(k):
            score += 1
    return round(100.0 * score / total, 2)
