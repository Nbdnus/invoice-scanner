import os, uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Invoice, InvoiceRawText
from app.extraction.text_reader import extract_text_from_pdf
from app.extraction.rules import parse_date, parse_amount, parse_invoice_number, guess_supplier, compute_confidence

app = FastAPI(title="Invoice Scanner", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

Base.metadata.create_all(bind=engine)

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

class InvoiceOut(BaseModel):
    id: int
    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    total_amount: float | None = None
    currency: str | None = None
    extraction_confidence: float | None = None
    needs_review: int | None = None
    class Config:
        from_attributes = True

@app.get("/")
def root():
    return {"status": "ok", "app": "invoice-scanner"}

@app.get("/invoices", response_model=List[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.id.desc()).all()

@app.post("/upload", response_model=InvoiceOut)
def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF allowed")
    uid = f"{uuid.uuid4()}.pdf"
    out_path = os.path.join(STORAGE_DIR, uid)
    with open(out_path, "wb") as f:
        f.write(file.file.read())

    raw_text = extract_text_from_pdf(out_path)

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
    db.add(inv); db.flush()
    db.add(InvoiceRawText(invoice_id=inv.id, raw_text=raw_text))
    db.commit(); db.refresh(inv)
    return inv
