import api from "./api";

export type InvoiceItem = {
  id: number;
  invoice_id: number;
  line_index?: number | null;
  description?: string | null;
  quantity?: number | null;
  unit?: string | null;
  unit_price?: number | null;
  vat_rate?: number | null;
  vat_amount?: number | null;
  line_total?: number | null;
};

export async function fetchItems(invoiceId: number): Promise<InvoiceItem[]> {
  const { data } = await api.get(`/invoices/${invoiceId}/items`);
  return data ?? [];
}
