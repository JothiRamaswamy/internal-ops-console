import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { getKycSummary, listKyc } from "@/api/queries";
import { CopyId, EmptyState, Loading, StatusBadge, SummaryCard } from "@/components/ui";
import { formatDateTime, timeAgo } from "@/lib/format";

const STATUSES = [
  "PENDING_VENDOR",
  "NEEDS_REVIEW",
  "REQUESTED_MORE_INFO",
  "APPROVED",
  "REJECTED",
];
const RISK = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const VENDORS = ["PERSONA", "STRIPE_IDENTITY", "MOCK_VENDOR"];

export function KycListPage() {
  const [params, setParams] = useSearchParams();
  const filters = {
    status: params.get("status") ?? "",
    risk_level: params.get("risk_level") ?? "",
    vendor: params.get("vendor") ?? "",
    country: params.get("country") ?? "",
    q: params.get("q") ?? "",
  };

  const summary = useQuery({ queryKey: ["kyc-summary"], queryFn: getKycSummary });
  const query = useQuery({
    queryKey: ["kyc-list", filters],
    queryFn: () => listKyc(filters),
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
          label="Awaiting review"
          value={summary.data?.awaiting_review ?? "—"}
        />
        <SummaryCard label="High-risk" value={summary.data?.high_risk ?? "—"} />
        <SummaryCard
          label="Oldest unreviewed"
          value={
            summary.data?.oldest_unreviewed_at
              ? timeAgo(summary.data.oldest_unreviewed_at)
              : "—"
          }
        />
        <SummaryCard
          label="Reviewed today"
          value={summary.data?.reviewed_today ?? "—"}
        />
      </div>

      <div className="card p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <div>
            <label className="label">Search</label>
            <input
              className="input"
              placeholder="Name, email, case ID"
              value={filters.q}
              onChange={(e) => setFilter("q", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Status</label>
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
          <div>
            <label className="label">Risk level</label>
            <select
              className="input"
              value={filters.risk_level}
              onChange={(e) => setFilter("risk_level", e.target.value)}
            >
              <option value="">All</option>
              {RISK.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Vendor</label>
            <select
              className="input"
              value={filters.vendor}
              onChange={(e) => setFilter("vendor", e.target.value)}
            >
              <option value="">All</option>
              {VENDORS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Country</label>
            <input
              className="input"
              placeholder="e.g. US"
              value={filters.country}
              onChange={(e) => setFilter("country", e.target.value.toUpperCase())}
            />
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
          <EmptyState message="No KYC cases match these filters." />
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50">
              <tr>
                <th className="th">Customer</th>
                <th className="th">Case ID</th>
                <th className="th">Vendor</th>
                <th className="th">Country</th>
                <th className="th">Risk</th>
                <th className="th">Status</th>
                <th className="th">Submitted</th>
                <th className="th">Age</th>
                <th className="th">Reviewer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {query.data.items.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="td">
                    <Link
                      to={`/kyc/${c.id}`}
                      className="font-medium text-brand-600 hover:underline"
                    >
                      {c.customer?.full_name ?? "—"}
                    </Link>
                    <div className="text-xs text-slate-400">
                      {c.customer?.email}
                    </div>
                  </td>
                  <td className="td">
                    <CopyId value={c.id} />
                  </td>
                  <td className="td">{c.vendor}</td>
                  <td className="td">{c.country_code}</td>
                  <td className="td">
                    <StatusBadge value={c.risk_level} />
                  </td>
                  <td className="td">
                    <StatusBadge value={c.status} />
                  </td>
                  <td className="td text-slate-500">
                    {formatDateTime(c.submitted_at)}
                  </td>
                  <td className="td text-slate-500">{timeAgo(c.submitted_at)}</td>
                  <td className="td text-slate-500">
                    {c.assigned_reviewer?.name ?? "Unassigned"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {query.data && (
        <div className="text-xs text-slate-400">
          {query.data.total} case(s)
        </div>
      )}
    </div>
  );
}
