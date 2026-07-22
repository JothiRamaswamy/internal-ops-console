import { useQuery } from "@tanstack/react-query";

import { getOverview } from "@/api/queries";
import { Loading, SummaryCard } from "@/components/ui";
import { formatMoney } from "@/lib/format";

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
    </div>
  );
}
