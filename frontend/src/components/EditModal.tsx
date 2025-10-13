import { useEffect, useState } from "react";
import type { Invoice } from "../lib/invoices";

type Props = {
  open: boolean;
  onClose: () => void;
  invoice: Invoice | null;
  onSave: (payload: Partial<Invoice>) => Promise<void>;
};

export default function EditModal({ open, onClose, invoice, onSave }: Props) {
  const [form, setForm] = useState<Partial<Invoice>>({});

  useEffect(() => {
    if (invoice) {
      setForm({
        supplier_name: invoice.supplier_name ?? "",
        invoice_number: invoice.invoice_number ?? "",
        invoice_date: invoice.invoice_date ?? "",
        total_amount: invoice.total_amount ?? null,
        currency: invoice.currency ?? "EUR",
        needs_review: invoice.needs_review ?? 1,
      });
    }
  }, [invoice]);

  if (!open || !invoice) return null;

  function setField<K extends keyof Invoice>(key: K, value: Invoice[K]) {
    setForm((prev: Partial<Invoice>) => ({ ...prev, [key]: value }));
  }

  const save = async () => {
    await onSave(form);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <div className="w-full max-w-xl rounded-2xl bg-white p-5 shadow-xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Rechnung bearbeiten #{invoice.id}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-700">✕</button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="col-span-2">
            <span className="text-xs text-slate-500">Lieferant</span>
            <input
              className="input"
              value={(form.supplier_name as string) ?? ""}
              onChange={(e) => setField("supplier_name", e.target.value as unknown as Invoice["supplier_name"])}
            />
          </label>

          <label>
            <span className="text-xs text-slate-500">Rechnungsnummer</span>
            <input
              className="input"
              value={(form.invoice_number as string) ?? ""}
              onChange={(e) => setField("invoice_number", e.target.value as unknown as Invoice["invoice_number"])}
            />
          </label>

          <label>
            <span className="text-xs text-slate-500">Datum (YYYY-MM-DD)</span>
            <input
              className="input"
              value={(form.invoice_date as string) ?? ""}
              onChange={(e) => setField("invoice_date", e.target.value as unknown as Invoice["invoice_date"])}
            />
          </label>

          <label>
            <span className="text-xs text-slate-500">Betrag</span>
            <input
              type="number"
              step="0.01"
              className="input"
              value={form.total_amount ?? ""}
              onChange={(e) => {
                const v = e.target.value === "" ? null : Number(e.target.value);
                setField("total_amount", v as Invoice["total_amount"]);
              }}
            />
          </label>

          <label>
            <span className="text-xs text-slate-500">Währung</span>
            <input
              className="input"
              value={form.currency ?? "EUR"}
              onChange={(e) => setField("currency", e.target.value as Invoice["currency"])}
            />
          </label>

          <label className="col-span-2 inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={(form.needs_review ?? 1) === 0}
              onChange={(e) => setField("needs_review", (e.target.checked ? 0 : 1) as Invoice["needs_review"])}
            />
            <span>Als geprüft markieren (setzt <code>needs_review</code> = 0)</span>
          </label>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">Abbrechen</button>
          <button onClick={save} className="btn-primary">Speichern</button>
        </div>
      </div>
    </div>
  );
}
