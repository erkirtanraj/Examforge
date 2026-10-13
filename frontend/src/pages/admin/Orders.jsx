import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { PageHeader, DataTable, Pill, rupees } from "../../components/admin/kit";

const TONE = { paid: "emerald", created: "amber", failed: "rose" };

export default function Orders() {
  const [orders, setOrders] = useState([]);
  useEffect(() => { api.get("/admin/orders").then((r) => setOrders(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Management" title="Orders" desc="Every enrollment and Razorpay payment." />
      <DataTable head={["Item", "Type", "Amount", "Status", "Razorpay payment", "Date"]} testid="orders-table"
                 empty={!orders.length ? "No orders yet." : null}>
        {orders.map((o) => (
          <tr key={o.id} className="border-t border-gray-800" data-testid={`order-row-${o.id}`}>
            <td className="p-3 text-white">{o.item_title || "—"}</td>
            <td className="p-3 text-gray-400 mono-font text-xs uppercase">{o.item_type.replace("_", " ")}</td>
            <td className="p-3 text-gray-300 mono-font">{rupees(o.amount)}</td>
            <td className="p-3"><Pill tone={TONE[o.status] || "gray"}>{o.status.toUpperCase()}</Pill></td>
            <td className="p-3 mono-font text-xs text-gray-500">{o.razorpay_payment_id || "—"}</td>
            <td className="p-3 text-gray-400 whitespace-nowrap">{new Date(o.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}
