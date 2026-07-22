import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { getPaymentsSummary, listPayments } from "@/api/queries";
import { EmptyState, Loading, StatusBadge, SummaryCard } from "@/components/ui";
import { formatDateTime, formatMoney } from "@/lib/format";

const STATUSES = [
  "SUCCEEDED",
  "PARTIALLY_REFUNDED",
  "FULLY_REFUNDED",
  "DISPUTED",
  "FAILED",
];

export function RefundsListPage() {
  const [params, setParams] = useSearchParams();
  const filters = {
    q: params.get("q") ?? "",
    order_id: params.get("order_id") ?? "",
    last4: params.get("last4") ?? "",
    status: params.get("status") ?? "",
  };

  const summary = useQuery({
    queryKey: ["payments-summary"],
    queryFn: getPaymentsSummary,
  });
  const query = useQuery({
    queryKey: ["payments-list", filters],
    queryFn: () => listPayments(filters),
  });

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };
  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard
          label="Gross volume"
          value={
            summary.data ? formatMoney(summary.data.gross_volume_minor) : "—"
          }
        />
        <SummaryCard
          label="Refunded today"
          value={
            summary.data ? formatMoney(summary.data.refunded_today_minor) : "—"
          }
        />
        <SummaryCard
          label="Refund rate"
          value={
            summary.data
              ? `${(summary.data.refund_rate * 100).toFixed(1)}%`
              : "—"
          }
        />
        <SummaryCard
          label="Failed refunds"
          value={summary.data?.failed_refunds ?? "—"}
        />
      </div>

      <div className="card p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div>
            <label className="label">Customer</label>
            <input
              className="input"
              placeholder="Name or email"
              value={filters.q}
              onChange={(e) => setFilter("q", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Order ID</label>
            <input
              className="input"
              value={filters.order_id}
              onChange={(e) => setFilter("order_id", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Last 4</label>
            <input
              className="input"
              value={filters.last4}
              onChange={(e) => setFilter("last4", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Payment status</label>
            <select
              className="input"
              value={filters.status}
              onChange={(e) => setFilter("status", e.target.value)}
            >
              <option value="">All</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
        {hasFilters && (
          <div className="mt-3">
            <button
              className="btn-secondary"
              onClick={() => setParams(new URLSearchParams())}
            >
              Reset filters
            </button>
          </div>
        )}
      </div>

      <div className="card overflow-hidden">
        {query.isLoading ? (
          <Loading />
        ) : !query.data || query.data.items.length === 0 ? (
          <EmptyState message="No payments match these filters." />
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50">
              <tr>
                <th className="th">Payment</th>
                <th className="th">Customer</th>
                <th className="th">Order</th>
                <th className="th">Amount</th>
                <th className="th">Refunded</th>
                <th className="th">Remaining</th>
                <th className="th">Payment status</th>
                <th className="th">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {query.data.items.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="td">
                    <Link
                      to={`/refunds/${p.id}`}
                      className="font-medium text-brand-600 hover:underline"
                    >
                      {p.id.slice(0, 12)}
                    </Link>
                    <div className="text-xs text-slate-400">
                      {p.payment_method_brand} ••{p.payment_method_last4}
                    </div>
                  </td>
                  <td className="td">{p.customer?.full_name}</td>
                  <td className="td text-slate-500">{p.order_id}</td>
                  <td className="td">{formatMoney(p.amount_minor, p.currency)}</td>
                  <td className="td">
                    {formatMoney(p.refunded_minor, p.currency)}
                  </td>
                  <td className="td">
                    {formatMoney(p.remaining_refundable_minor, p.currency)}
                  </td>
                  <td className="td">
                    <StatusBadge
                      value={p.status}
                      label={p.status === "SUCCEEDED" ? "Payment succeeded" : undefined}
                    />
                  </td>
                  <td className="td text-slate-500">
                    {formatDateTime(p.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {query.data && (
        <div className="text-xs text-slate-400">{query.data.total} payment(s)</div>
      )}
    </div>
  );
}
