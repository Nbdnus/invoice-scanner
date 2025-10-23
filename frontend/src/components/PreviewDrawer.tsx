import { useEffect } from "react";

type Props = {
  open: boolean;
  title?: string;
  pdfUrl?: string | null;
  onClose: () => void;
};

export default function PreviewDrawer({ open, title, pdfUrl, onClose }: Props) {
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [onClose]);

  if (!open) return null;

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer translate-x-0">
        <div className="flex items-center justify-between border-b px-5 py-3">
          <h3 className="text-lg font-semibold">{title ?? "Vorschau"}</h3>
          <button className="text-slate-500 hover:text-slate-700" onClick={onClose}>✕</button>
        </div>
        <div className="h-[calc(100%-56px)]">
          {pdfUrl ? (
            <iframe title="PDF" src={pdfUrl} className="h-full w-full" />
          ) : (
            <div className="p-5 text-slate-500">Kein Dokument vorhanden.</div>
          )}
        </div>
      </aside>
    </>
  );
}
