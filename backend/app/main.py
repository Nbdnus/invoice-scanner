import os
import uuid
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
app = FastAPI(title="Invoice Scanner", version="0.1.0")
from .db import Base, engine, get_db
from .models import Invoice, InvoiceRawText
from app.extraction.text_reader import extract_text_from_pdf
from app.extraction.rules import (
    parse_date, parse_amount, parse_invoice_number,
    guess_supplier, compute_confidence
)
from fastapi.staticfiles import StaticFiles
# ...
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=STORAGE_DIR), name="files")




from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,  # wir senden keine Cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


# Tabellen sicherstellen
Base.metadata.create_all(bind=engine)

# Upload-Speicher
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)


# ---------- Schemas ----------
class InvoiceOut(BaseModel):
    id: int
    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    total_amount: float | None = None
    currency: str | None = None
    extraction_confidence: float | None = None
    needs_review: int | None = None
    source_file: str | None = None  # <— NEU

    class Config:
        from_attributes = True



class InvoiceUpdate(BaseModel):
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None    # ISO "YYYY-MM-DD"
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    needs_review: Optional[int] = None


# ---------- Basic health ----------
@app.get("/")
def root():
    return {"status": "ok", "app": "invoice-scanner"}


# ---------- List / optional filter ----------
@app.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(
    needs_review: Optional[int] = Query(None, description="Optional: 0 oder 1 zum Filtern"),
    db: Session = Depends(get_db)
):
    q = db.query(Invoice).order_by(Invoice.id.desc())
    if needs_review in (0, 1):
        q = q.filter(Invoice.needs_review == needs_review)
    return q.all()


# ---------- Detail ----------
@app.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Not found")
    return inv


# ---------- Update (manuelle Korrekturen) ----------
@app.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate = Body(...),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(inv, k, v)

    db.commit()
    db.refresh(inv)
    return inv


# ---------- Upload & Extraktion ----------
@app.post("/upload", response_model=InvoiceOut)
def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF allowed")

    # Datei speichern
    uid = f"{uuid.uuid4()}.pdf"
    out_path = os.path.join(STORAGE_DIR, uid)
    with open(out_path, "wb") as f:
        f.write(file.file.read())

    # Text extrahieren (inkl. OCR-Fallback in text_reader.py)
    raw_text = extract_text_from_pdf(out_path)

    # Felder parsen
    parsed = {
        "supplier_name": guess_supplier(raw_text),
        "invoice_date": parse_date(raw_text),
        "invoice_number": parse_invoice_number(raw_text),
    }
    amt = parse_amount(raw_text)
    if amt:
        parsed["total_amount"], parsed["currency"] = amt[0], amt[1]

    confidence = compute_confidence(parsed)
    needs_review = 1 if confidence < 75.0 else 0

    inv = Invoice(
        supplier_name=parsed.get("supplier_name"),
        invoice_number=parsed.get("invoice_number"),
        invoice_date=parsed.get("invoice_date"),
        total_amount=parsed.get("total_amount"),
        currency=parsed.get("currency") or "EUR",
        source_file=uid,
        extraction_confidence=confidence,
        needs_review=needs_review,
    )
    db.add(inv)
    db.flush()  # ID holen

    db.add(InvoiceRawText(invoice_id=inv.id, raw_text=raw_text))
    db.commit()
    db.refresh(inv)
    return inv
