// frontend/src/components/PreviewDrawer.tsx
import { useState } from "react";
import ItemsTable from "./ItemsTable";

type Props = {
  open: boolean;
  title?: string | null;
  pdfUrl: string | null;
  onClose: () => void;
  invoiceId?: number | null;
};

export default function PreviewDrawer({ open, title, pdfUrl, onClose, invoiceId }: Props) {
  if (!open) return null; // <— wichtigste Änderung: nur rendern, wenn offen

  return (
    <div aria-modal className="fixed inset-0 z-[100]">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/30"
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className="absolute right-0 top-0 h-full w-full max-w-[900px] bg-white shadow-2xl flex flex-col animate-slide-in"
        role="dialog"
        aria-label="Dokumentvorschau"
      >
        <div className="flex items-center justify-between border-b p-4">
          <h2 className="text-lg font-semibold">{title ?? "Vorschau"}</h2>
          <button className="btn-secondary" onClick={onClose}>Schließen</button>
        </div>

        {/* Tabs */}
        <Tabs
          pdfUrl={pdfUrl}
          invoiceId={invoiceId ?? null}
        />
      </div>

      <style>{`
        @keyframes slide-in { from { transform: translateX(100%);} to { transform: translateX(0);} }
        .animate-slide-in { animation: slide-in .18s ease-out; }
      `}</style>
    </div>
  );
}

function Tabs({ pdfUrl, invoiceId }: { pdfUrl: string | null; invoiceId: number | null }) {
  const [tab, setTab] = useState<"doc" | "items">("doc");

  return (
    <>
      <div className="px-4 pt-3">
        <div className="flex gap-2">
          <button
            className={`tab ${tab === "doc" ? "tab-active" : ""}`}
            onClick={() => setTab("doc")}
          >
            Dokument
          </button>
          <button
            className={`tab ${tab === "items" ? "tab-active" : ""}`}
            onClick={() => setTab("items")}
          >
            Positionen
          </button>
        </div>
      </div>

      <div className="p-4 grow overflow-hidden">
        {tab === "doc" && (
          pdfUrl ? (
            <iframe
              title="PDF Preview"
              className="w-full h-full rounded border"
              src={pdfUrl}
            />
          ) : (
            <div className="text-sm text-slate-500">Kein PDF verfügbar.</div>
          )
        )}

        {tab === "items" && (
          <div className="h-full overflow-auto">
            {invoiceId ? (
              <ItemsTable invoiceId={invoiceId} />
            ) : (
              <div className="text-sm text-slate-500">Keine Rechnungs-ID übergeben.</div>
            )}
          </div>
        )}
      </div>

      <style>{`
        .tab { padding: .5rem .75rem; border-radius: .5rem; }
        .tab-active { background: #e2e8f0; }
      `}</style>
    </>
  );
}
