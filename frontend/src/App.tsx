import { useCallback, useEffect, useState } from "react";
import { fetchInvoices, patchInvoice, type Invoice } from "./lib/invoices";
import EditModal from "./components/EditModal";

export default function App() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [needs, setNeeds] = useState<"" | "0" | "1">("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [editing, setEditing] = useState<Invoice | null>(null);

  const load = useCallback(async () => {
    const n = needs === "" ? undefined : (Number(needs) as 0 | 1);
    const data = await fetchInvoices(n);
    setInvoices(data);
  }, [needs]);

  useEffect(() => { load(); }, [load]);

  const onUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setMsg("Bitte PDF auswählen"); return; }
    try {
      setLoading(true);
      const fd = new FormData();
      fd.append("file", file);
      setMsg("Upload erfolgreich");
      setFile(null);
      await load();
    } catch {
      setMsg("Upload fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  const onSaveEdit = async (payload: Partial<Invoice>) => {
    if (!editing) return;
    await patchInvoice(editing.id, payload);
    await load();
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl p-6">
        <header className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Invoice Scanner — Admin</h1>
          <div className="flex items-center gap-3">
            <select value={needs} onChange={(e)=>setNeeds(e.target.value as "" | "0" | "1")} className="input !w-40">
              <option value="">Alle</option>
              <option value="1">Nur Review nötig</option>
              <option value="0">Nur OK</option>
            </select>
            <form onSubmit={onUpload} className="flex items-center gap-2">
              <input type="file" accept="application/pdf" onChange={(e)=>setFile(e.target.files?.[0] ?? null)} />
              <button disabled={loading} className="btn-primary">{loading ? "Lädt..." : "Hochladen"}</button>
            </form>
          </div>
        </header>

        {msg && <div className="mb-4 rounded-xl bg-slate-200 px-3 py-2 text-slate-800">{msg}</div>}

        <div className="rounded-2xl bg-white p-4 shadow">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="py-2">ID</th>
                <th>Lieferant</th>
                <th>Re-Nr.</th>
                <th>Datum</th>
                <th>Betrag</th>
                <th>Währung</th>
                <th>Confidence</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {invoices.map(inv => (
                <tr key={inv.id} className="border-t">
                  <td className="py-2">{inv.id}</td>
                  <td>{inv.supplier_name ?? "-"}</td>
                  <td>{inv.invoice_number ?? "-"}</td>
                  <td>{inv.invoice_date ?? "-"}</td>
                  <td>{inv.total_amount ?? "-"}</td>
                  <td>{inv.currency ?? "-"}</td>
                  <td>{inv.extraction_confidence ?? "-"}</td>
                  <td>{inv.needs_review ? <span className="badge-review">Review</span> : <span className="badge-ok">OK</span>}</td>
                  <td>
                    <div className="flex gap-2">
                      <button className="btn-secondary" onClick={()=>setEditing(inv)}>Bearbeiten</button>
                      {inv.source_file && (
                        <a
                          className="btn-secondary"
                          href={`${import.meta.env.VITE_API_URL}/files/${inv.source_file}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          PDF
                        </a>
                      )}
                    </div>
                  </td>

                </tr>
              ))}
            </tbody>
          </table>

          {invoices.length === 0 && <p className="mt-3 text-sm text-slate-500">Noch keine Rechnungen.</p>}
        </div>
      </div>

      <EditModal
        open={!!editing}
        invoice={editing}
        onClose={()=>setEditing(null)}
        onSave={onSaveEdit}
      />
    </div>
  );
}
