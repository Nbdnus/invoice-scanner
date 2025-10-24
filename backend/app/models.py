from sqlalchemy import Column, Integer, Float, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base  # <-- WICHTIG: Base aus app.db importieren, KEIN declarative_base() hier!

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(255), nullable=True)
    invoice_number = Column(String(255), nullable=True)
    invoice_date = Column(String(32), nullable=True)
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
    line_index = Column(Integer, nullable=True)
    description = Column(String(1024), nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(64), nullable=True)
    unit_price = Column(Float, nullable=True)
    vat_rate = Column(Float, nullable=True)
    vat_amount = Column(Float, nullable=True)
    line_total = Column(Float, nullable=True)
    invoice = relationship("Invoice", back_populates="items")
