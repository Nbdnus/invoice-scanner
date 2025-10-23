import { useCallback, useEffect, useMemo, useState } from "react";
import api from "./lib/api";
import { fetchInvoices, patchInvoice, deleteInvoice, type Invoice } from "./lib/invoices";
import EditModal from "./components/EditModal";
import Toast from "./components/Toast";
import PreviewDrawer from "./components/PreviewDrawer";

type SortKey = "id" | "supplier_name" | "invoice_date" | "total_amount" | "extraction_confidence";

export default function App() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [needs, setNeeds] = useState<"" | "0" | "1">("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{kind: "success"|"error"|"info"; text: string} | null>(null);
  const [editing, setEditing] = useState<Invoice | null>(null);
  const [lastLoadedAt, setLastLoadedAt] = useState<Date | null>(null);

  // UI state
  const [q, setQ] = useState("");
  const [sortBy, setSortBy] = useState<SortKey>("id");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [previewOf, setPreviewOf] = useState<Invoice | null>(null);

  // Files-URL: VITE_API_URL oder Proxy /api
  const filesUrl = useCallback((path: string) => {
    const base = (import.meta.env.VITE_API_URL as string | undefined) || "";
    return base ? `${base}${path}` : `/api${path}`;
  }, []);

  const load = useCallback(async () => {
    const n = needs === "" ? undefined : (Number(needs) as 0 | 1);
    const data = await fetchInvoices(n);
    setInvoices(data);
    setLastLoadedAt(new Date());
  }, [needs]);

  useEffect(() => { load(); }, [load]);

  const onUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setToast({kind:"info", text:"Bitte PDF auswählen"}); return; }
    try {
      setLoading(true);
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.post("/upload", fd);
      console.log("Upload response:", res.data);
      setToast({kind:"success", text:"Upload erfolgreich"});
      setFile(null);
      await load();
      setTimeout(() => load(), 300);
    } catch (err) {
      console.error("Upload failed", err);
      setToast({kind:"error", text:"Upload fehlgeschlagen"});
    } finally {
      setLoading(false);
    }
  };

  const onSaveEdit = async (payload: Partial<Invoice>) => {
    if (!editing) return;
    await patchInvoice(editing.id, payload);
    setToast({kind:"success", text:"Gespeichert"});
    await load();
  };

  const onDelete = async (id: number) => {
    if (!confirm("Möchtest du diese Rechnung wirklich löschen?")) return;
    try {
      setLoading(true);
      await deleteInvoice(id);
      setToast({kind:"success", text:"Rechnung gelöscht"});
      await load();
    } catch (err) {
      console.error("Löschen fehlgeschlagen", err);
      setToast({kind:"error", text:"Fehler beim Löschen"});
    } finally {
      setLoading(false);
    }
  };

const filtered = useMemo(() => {
  const term = q.trim().toLowerCase();

  const passSearch = (inv: Invoice) =>
    (inv.supplier_name ?? "").toLowerCase().includes(term) ||
    (inv.invoice_number ?? "").toLowerCase().includes(term) ||
    String(inv.id).includes(term);

  const list = term ? invoices.filter(passSearch) : invoices;

  // Mappe SortKey → Werttyp
  const getKeyValue = (inv: Invoice, key: SortKey): string | number | null => {
    switch (key) {
      case "id": return inv.id;
      case "supplier_name": return inv.supplier_name ?? null;
      case "invoice_date": return inv.invoice_date ?? null;
      case "total_amount": return inv.total_amount ?? null;
      case "extraction_confidence": return inv.extraction_confidence ?? null;
    }
  };

  const compare = (a: Invoice, b: Invoice): number => {
    const va = getKeyValue(a, sortBy);
    const vb = getKeyValue(b, sortBy);

    // Nulls nach hinten
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;

    // Zahl vs. String getrennt vergleichen
    const dir = sortDir === "asc" ? 1 : -1;
    if (typeof va === "number" && typeof vb === "number") {
      return va < vb ? -1 * dir : va > vb ? 1 * dir : 0;
    }
    const sa = String(va).toLowerCase();
    const sb = String(vb).toLowerCase();
    if (sa < sb) return -1 * dir;
    if (sa > sb) return 1 * dir;
    return 0;
  };

  return [...list].sort(compare);
}, [invoices, q, sortBy, sortDir]);

  const stats = useMemo(() => {
    const total = invoices.length;
    const review = invoices.filter(i => i.needs_review === 1).length;
    const avgConf = invoices.length
      ? Math.round((invoices.map(i => i.extraction_confidence ?? 0).reduce((x,y)=>x+y,0) / invoices.length) * 10) / 10
      : 0;
    return { total, review, avgConf };
  }, [invoices]);

  const lastUpdatedLabel = useMemo(() => {
    if (!lastLoadedAt) return "";
    const d = lastLoadedAt;
    return d.toLocaleTimeString();
  }, [lastLoadedAt]);

  const headerBtn = (key: SortKey, label: string) => (
    <button
      className="text-left"
      onClick={() => {
        if (sortBy === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
        else { setSortBy(key); setSortDir("asc"); }
      }}
      title="Sortieren"
    >
      {label}{sortBy === key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
    </button>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <h1 className="text-2xl font-bold">Invoice Scanner — Admin</h1>
          <div className="flex flex-wrap items-center gap-3">
            <input
              className="input !w-56"
              placeholder="Suchen (ID, Lieferant, Re-Nr.)"
              value={q}
              onChange={(e)=>setQ(e.target.value)}
            />
            <select value={needs} onChange={(e)=>setNeeds(e.target.value as ""|"0"|"1")} className="input !w-44">
              <option value="">Alle</option>
              <option value="1">Nur Review nötig</option>
              <option value="0">Nur OK</option>
            </select>
            <form onSubmit={onUpload} className="flex items-center gap-2">
              <input type="file" accept="application/pdf" onChange={(e)=>setFile(e.target.files?.[0] ?? null)} />
              <button disabled={loading} className="btn-primary">{loading ? "Lädt..." : "Hochladen"}</button>
            </form>
          </div>
        </div>

        {/* Stat Cards */}
        <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="card">
            <div className="text-slate-500 text-sm">Gesamt</div>
            <div className="text-2xl font-semibold">{stats.total}</div>
          </div>
          <div className="card">
            <div className="text-slate-500 text-sm">Review offen</div>
            <div className="text-2xl font-semibold">{stats.review}</div>
          </div>
          <div className="card">
            <div className="text-slate-500 text-sm">Ø Confidence</div>
            <div className="text-2xl font-semibold">{stats.avgConf || "-"}</div>
          </div>
        </section>

        {/* Tabelle */}
        <div className="card">
          <div className="mb-2 text-right text-xs text-slate-500">
            {lastUpdatedLabel && <>Zuletzt aktualisiert: {lastUpdatedLabel}</>}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-2">{headerBtn("id", "ID")}</th>
                  <th>{headerBtn("supplier_name", "Lieferant")}</th>
                  <th>Re-Nr.</th>
                  <th>{headerBtn("invoice_date", "Datum")}</th>
                  <th>{headerBtn("total_amount", "Betrag")}</th>
                  <th>Währung</th>
                  <th>{headerBtn("extraction_confidence", "Confidence")}</th>
                  <th>Status</th>
                  <th>Dokument</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {!invoices.length && (
                  <tr><td colSpan={10} className="py-6 text-center text-slate-500">Noch keine Rechnungen.</td></tr>
                )}
                {!!invoices.length && filtered.map(inv => (
                  <tr key={inv.id} className="border-t tr-hover">
                    <td className="py-2">{inv.id}</td>
                    <td>{inv.supplier_name ?? "-"}</td>
                    <td>{inv.invoice_number ?? "-"}</td>
                    <td>{inv.invoice_date ?? "-"}</td>
                    <td>{inv.total_amount ?? "-"}</td>
                    <td>{inv.currency ?? "-"}</td>
                    <td className={
                      inv.extraction_confidence == null ? "text-slate-500" :
                      inv.extraction_confidence >= 75 ? "text-green-700" :
                      inv.extraction_confidence >= 40 ? "text-yellow-700" : "text-red-700"
                    }>
                      {inv.extraction_confidence ?? "-"}
                    </td>
                    <td>{inv.needs_review ? <span className="badge-review">Review</span> : <span className="badge-ok">OK</span>}</td>
                    <td>
                      {inv.source_file ? (
                        <div className="flex gap-2">
                          <button className="btn-secondary" onClick={()=>setPreviewOf(inv)}>Preview</button>
                          <a className="btn-secondary" href={filesUrl(`/files/${inv.source_file}`)} target="_blank" rel="noreferrer">PDF</a>
                        </div>
                      ) : <span className="text-slate-400">–</span>}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button className="btn-secondary" onClick={()=>setEditing(inv)}>Bearbeiten</button>
                        <button className="btn-danger" onClick={()=>onDelete(inv.id)}>Löschen</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {/* Skeleton (kurz sichtbar beim Laden) */}
                {loading && (
                  <tr>
                    <td colSpan={10} className="py-3">
                      <div className="flex gap-2">
                        <div className="skeleton h-4 w-24" />
                        <div className="skeleton h-4 w-40" />
                        <div className="skeleton h-4 w-28" />
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Modals / UI Layer */}
      <EditModal open={!!editing} invoice={editing} onClose={()=>setEditing(null)} onSave={onSaveEdit} />

      <PreviewDrawer
        open={!!previewOf}
        title={previewOf ? `Rechnung #${previewOf.id}` : "Vorschau"}
        pdfUrl={previewOf?.source_file ? filesUrl(`/files/${previewOf.source_file}`) : null}
        onClose={()=>setPreviewOf(null)}
      />

      {toast && <Toast kind={toast.kind} message={toast.text} onClose={()=>setToast(null)} />}
    </div>
  );
}
