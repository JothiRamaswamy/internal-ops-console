import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { ApiRequestError } from "@/api/client";
import {
  getPersonaRows,
  getStripeRows,
  listIntegrations,
  runIntegrationSync,
  type IntegrationHealth,
} from "@/api/queries";
import { useAuth } from "@/auth/AuthContext";
import { useToast } from "@/components/Toast";
import { EmptyState, Loading } from "@/components/ui";
import { formatDateTime, formatMoney, timeAgo } from "@/lib/format";

function HealthCard({ it }: { it: IntegrationHealth }) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-800">{it.name}</div>
          <div className="text-xs text-slate-400">{it.category}</div>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          Connected
        </span>
      </div>
      <dl className="mt-3 space-y-1.5 text-xs">
        <div className="flex justify-between">
          <dt className="text-slate-400">Records synced</dt>
          <dd className="font-medium text-slate-700">{it.record_count}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-400">Last synced</dt>
          <dd className="font-medium text-slate-700">
            {it.last_synced_at ? timeAgo(it.last_synced_at) : "Never"}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-400">Next sync</dt>
          <dd className="font-medium text-slate-700">
            {it.next_sync_at ? formatDateTime(it.next_sync_at) : "—"}
          </dd>
        </div>
      </dl>
    </div>
  );
}

function PersonaTable() {
  const q = useQuery({
    queryKey: ["integration-rows", "persona"],
    queryFn: getPersonaRows,
  });
  if (q.isLoading) return <Loading />;
  const rows = q.data?.items ?? [];
  if (rows.length === 0) return <EmptyState message="No synced rows." />;
  return (
    <div className="overflow-auto">
      <table className="w-full">
        <thead className="border-b border-slate-100 bg-slate-50">
          <tr>
            <th className="th">Inquiry</th>
            <th className="th">Name</th>
            <th className="th">Status</th>
            <th className="th">Country</th>
            <th className="th">Risk</th>
            <th className="th">Received</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={r.inquiry_id} className="hover:bg-slate-50">
              <td className="td font-mono text-xs">{r.inquiry_id}</td>
              <td className="td">
                {r.name || "—"}
                <div className="text-xs text-slate-400">{r.email}</div>
              </td>
              <td className="td capitalize">{r.status}</td>
              <td className="td">{r.country_code ?? "—"}</td>
              <td className="td">{r.risk_score ?? "—"}</td>
              <td className="td text-slate-500">
                {r.created_at ? timeAgo(r.created_at) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StripeTable() {
  const q = useQuery({
    queryKey: ["integration-rows", "stripe"],
    queryFn: getStripeRows,
  });
  if (q.isLoading) return <Loading />;
  const rows = q.data?.items ?? [];
  if (rows.length === 0) return <EmptyState message="No synced rows." />;
  return (
    <div className="overflow-auto">
      <table className="w-full">
        <thead className="border-b border-slate-100 bg-slate-50">
          <tr>
            <th className="th">Charge</th>
            <th className="th">Customer</th>
            <th className="th">Amount</th>
            <th className="th">Refunded</th>
            <th className="th">Status</th>
            <th className="th">Card</th>
            <th className="th">Received</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={r.charge_id} className="hover:bg-slate-50">
              <td className="td font-mono text-xs">{r.charge_id}</td>
              <td className="td">{r.customer_email ?? "—"}</td>
              <td className="td">
                {formatMoney(r.amount, r.currency.toUpperCase())}
              </td>
              <td className="td">
                {r.amount_refunded > 0
                  ? formatMoney(r.amount_refunded, r.currency.toUpperCase())
                  : "—"}
              </td>
              <td className="td capitalize">{r.status}</td>
              <td className="td text-slate-500">
                {r.card_brand ? `${r.card_brand} ····${r.card_last4}` : "—"}
              </td>
              <td className="td text-slate-500">
                {r.created_at ? timeAgo(r.created_at) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function IntegrationsPage() {
  const { me } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const canSync = me?.role === "ADMIN" || me?.role === "OPS_REVIEWER";
  const integrations = useQuery({
    queryKey: ["integrations"],
    queryFn: listIntegrations,
  });

  const sync = useMutation({
    mutationFn: runIntegrationSync,
    onSuccess: ({ result }) => {
      const k = result.persona_kyc;
      const p = result.stripe_payments;
      toast.success(
        `Sync complete — KYC: +${k.created}/~${k.updated}, ` +
          `Payments: +${p.created}/~${p.updated}`,
      );
      void queryClient.invalidateQueries();
    },
    onError: (e) =>
      toast.error(e instanceof ApiRequestError ? e.message : "Sync failed."),
  });

  const lastSynced = integrations.data?.last_synced_at;
  const nextSync = integrations.data?.next_sync_at;
  const interval = integrations.data?.sync_interval_minutes;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4 rounded-md bg-blue-50 px-4 py-3 text-sm text-blue-800">
        <p>
          A scheduled <strong>sync/ETL</strong> job pulls each vendor into its
          staging table and normalizes it into the domain tables (KYC cases,
          payments)
          {interval ? ` — nominally every ${interval} minutes` : ""}. Last synced{" "}
          <strong>{lastSynced ? timeAgo(lastSynced) : "never"}</strong>
          {nextSync ? `; next around ${formatDateTime(nextSync)}` : ""}.
        </p>
        {canSync && (
          <button
            onClick={() => sync.mutate()}
            disabled={sync.isPending}
            className="btn-primary flex shrink-0 items-center gap-2"
          >
            <RefreshCw
              size={14}
              className={sync.isPending ? "animate-spin" : ""}
            />
            {sync.isPending ? "Syncing…" : "Sync now"}
          </button>
        )}
      </div>

      {integrations.isLoading ? (
        <Loading />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {(integrations.data?.integrations ?? []).map((it) => (
            <HealthCard key={it.key} it={it} />
          ))}
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-800">
            Persona — recent synced inquiries
          </h3>
        </div>
        <PersonaTable />
      </div>

      <div className="card overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-800">
            Stripe — recent synced charges
          </h3>
        </div>
        <StripeTable />
      </div>
    </div>
  );
}
