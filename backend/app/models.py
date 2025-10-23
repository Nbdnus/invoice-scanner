from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from .db import Base
from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(255))
    invoice_number = Column(String(100))
    invoice_date = Column(Date)
    total_amount = Column(Numeric(12, 2))
    currency = Column(String(10), default="EUR")
    vat_amount = Column(Numeric(12, 2))
    source_file = Column(String(500))
    extraction_confidence = Column(Numeric(5, 2))
    needs_review = Column(Integer, default=0)  # 0/1
    created_at = Column(DateTime, server_default=func.now())

    raw_text = relationship("InvoiceRawText", back_populates="invoice", uselist=False, cascade="all, delete-orphan")

class InvoiceRawText(Base):
    __tablename__ = "invoice_raw_text"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, unique=True)
    raw_text = Column(Text, nullable=False)

    invoice = relationship("Invoice", back_populates="raw_text")
class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False)
    line_index = Column(Integer, nullable=True)
    description = Column(String(1024), nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(64), nullable=True)
    unit_price = Column(Float, nullable=True)
    vat_rate = Column(Float, nullable=True)       # z.B. 19.0
    vat_amount = Column(Float, nullable=True)
    line_total = Column(Float, nullable=True)

    invoice = relationship("Invoice", backref="items")