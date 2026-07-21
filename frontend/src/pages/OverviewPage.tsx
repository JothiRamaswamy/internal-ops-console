import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getOverview } from "@/api/queries";
import { EmptyState, Loading, SummaryCard } from "@/components/ui";
import { formatDateTime, formatMoney, titleCase } from "@/lib/format";

export function OverviewPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["overview"],
    queryFn: getOverview,
  });

  if (isLoading || !data) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <SummaryCard label="KYC awaiting review" value={data.kyc_awaiting_review} />
        <SummaryCard label="KYC high-risk" value={data.kyc_high_risk} />
        <SummaryCard
          label="Refund volume today"
          value={formatMoney(data.refund_volume_today_minor)}
        />
        <SummaryCard label="Failed refunds" value={data.failed_refunds} />
        <SummaryCard label="Prod flags enabled" value={data.prod_flags_enabled} />
        <SummaryCard
          label="Prod changes (7d)"
          value={data.prod_flag_changes_last_7d}
        />
      </div>

      <div className="card">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">
            Recent audit activity
          </h2>
          <Link to="/audit" className="text-sm text-brand-600 hover:underline">
            View all
          </Link>
        </div>
        {data.recent_audit.length === 0 ? (
          <EmptyState message="No audit activity yet." />
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-100">
              <tr>
                <th className="th">Time</th>
                <th className="th">Actor</th>
                <th className="th">Action</th>
                <th className="th">Entity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.recent_audit.map((e) => (
                <tr key={e.id}>
                  <td className="td text-slate-500">
                    {formatDateTime(e.created_at)}
                  </td>
                  <td className="td">{e.actor?.name ?? "System"}</td>
                  <td className="td font-medium">{titleCase(e.action)}</td>
                  <td className="td text-slate-500">
                    {e.entity_type} · {e.entity_id.slice(0, 10)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
