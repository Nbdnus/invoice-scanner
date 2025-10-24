// frontend/src/components/ItemsTable.tsx
import { useEffect, useMemo, useState } from "react";
import type { InvoiceItem } from "../lib/items";
import { fetchItems } from "../lib/items";

export default function ItemsTable({ invoiceId }: { invoiceId: number }) {
  const [items, setItems] = useState<InvoiceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setErr(null);
        setLoading(true);
        const data = await fetchItems(invoiceId);
        if (alive) setItems(data);
      } catch (e) {
        console.error("fetchItems failed", e);
        if (alive) setErr("Positionen konnten nicht geladen werden.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [invoiceId]);

  const totals = useMemo(() => {
    const sum = items.reduce((acc, it) => acc + (it.line_total ?? 0), 0);
    return { sum: Math.round(sum * 100) / 100 };
  }, [items]);

  if (loading) {
    return (
      <div className="p-3">
        <div className="skeleton h-4 w-32 mb-2" />
        <div className="skeleton h-4 w-64 mb-2" />
        <div className="skeleton h-4 w-40" />
      </div>
    );
  }

  if (err) {
    return <div className="p-3 text-sm text-red-700">{err}</div>;
  }

  if (!items.length) {
    return <div className="p-3 text-sm text-slate-500">Keine Positionen erkannt.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th className="py-2 w-14">#</th>
            <th>Beschreibung</th>
            <th className="w-24 text-right">Menge</th>
            <th className="w-28 text-right">Einzelpreis</th>
            <th className="w-28 text-right">Zeilensumme</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="py-2">{it.line_index ?? "-"}</td>
              <td>{it.description ?? "-"}</td>
              <td className="text-right">{it.quantity ?? "-"}</td>
              <td className="text-right">{it.unit_price ?? "-"}</td>
              <td className="text-right font-medium">{it.line_total ?? "-"}</td>
            </tr>
          ))}
          <tr className="border-t">
            <td colSpan={4} className="py-2 text-right text-slate-600">Summe (aus Positionen)</td>
            <td className="text-right font-semibold">{totals.sum}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
