import api from "./api";

export type Invoice = {
  id: number;
  supplier_name?: string | null;
  invoice_number?: string | null;
  invoice_date?: string | null;
  total_amount?: number | null;
  currency?: string | null;
  extraction_confidence?: number | null;
  needs_review?: number | null;
  source_file?: string | null; // <— NEU
};


export async function fetchInvoices(needs?: 0 | 1) {
  const url = needs === 0 || needs === 1 ? `/invoices?needs_review=${needs}` : "/invoices";
  const res = await api.get<Invoice[]>(url);
  return res.data;
}

export async function patchInvoice(id: number, payload: Partial<Invoice>) {
  const res = await api.patch<Invoice>(`/invoices/${id}`, payload);
  return res.data;
}

export async function deleteInvoice(id: number): Promise<void> {
  await api.delete(`/invoices/${id}`);
}

