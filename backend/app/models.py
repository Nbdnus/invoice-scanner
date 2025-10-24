from sqlalchemy import Column, Integer, Float, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

# WICHTIG: In deinem Projekt kommt Base aus app.db.
# Wenn du Base bereits aus .db importierst, kommentiere die Zeile unten aus
# und lass "from app.db import Base" in main.py bestehen.
Base = declarative_base()

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(255), nullable=True)
    invoice_number = Column(String(255), nullable=True)
    invoice_date = Column(String(32), nullable=True)   # ISO "YYYY-MM-DD" oder Roh-String
    total_amount = Column(Float, nullable=True)
    currency = Column(String(8), nullable=True)
    source_file = Column(String(512), nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    needs_review = Column(Integer, nullable=True, default=1)

    raw_texts = relationship("InvoiceRawText", back_populates="invoice", cascade="all, delete-orphan")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceRawText(Base):
    __tablename__ = "invoice_raw_text"
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False)
    raw_text = Column(Text, nullable=True)

    invoice = relationship("Invoice", back_populates="raw_texts")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False)

    # Reihenfolge/Originalindex in der Tabelle
    line_index = Column(Integer, nullable=True)

    # Inhalte
    description = Column(String(1024), nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(64), nullable=True)
    unit_price = Column(Float, nullable=True)
    vat_rate = Column(Float, nullable=True)    # z.B. 19.0
    vat_amount = Column(Float, nullable=True)
    line_total = Column(Float, nullable=True)

    invoice = relationship("Invoice", back_populates="items")
