import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  getLaunchDarkly,
  getPersona,
  getStripe,
  listIntegrations,
} from "@/api/queries";
import { EmptyState, Loading } from "@/components/ui";

type SourceKey = "persona" | "stripe" | "launchdarkly";

const SOURCES: Record<SourceKey, () => Promise<{ items: Record<string, unknown>[] }>> = {
  persona: getPersona,
  stripe: getStripe,
  launchdarkly: getLaunchDarkly,
};

function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (rows.length === 0) return <EmptyState message="No rows." />;
  const columns = Object.keys(rows[0]).filter((c) => c !== "raw");
  return (
    <div className="overflow-auto">
      <table className="w-full">
        <thead className="border-b border-slate-100 bg-slate-50">
          <tr>
            {columns.map((c) => (
              <th key={c} className="th">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r, i) => (
            <tr key={i} className="hover:bg-slate-50">
              {columns.map((c) => (
                <td key={c} className="td max-w-xs truncate">
                  {r[c] === null || r[c] === undefined
                    ? "—"
                    : typeof r[c] === "object"
                      ? JSON.stringify(r[c])
                      : String(r[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function IntegrationsPage() {
  const [active, setActive] = useState<SourceKey>("persona");
  const integrations = useQuery({
    queryKey: ["integrations"],
    queryFn: listIntegrations,
  });
  const source = useQuery({
    queryKey: ["integration-source", active],
    queryFn: () => SOURCES[active](),
  });

  return (
    <div className="space-y-5">
      <div className="rounded-md bg-blue-50 px-4 py-3 text-sm text-blue-800">
        These tables are <strong>mock representations</strong> of external data
        sources this console would integrate with. In production, adapters sync
        from the live vendor APIs; here the data is seeded for demonstration.
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {(integrations.data?.integrations ?? []).map((it) => (
          <div key={it.key} className="card p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-800">
                  {it.name}
                </div>
                <div className="text-xs text-slate-400">{it.category}</div>
              </div>
              <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                Connected
              </span>
            </div>
            <div className="mt-3 text-2xl font-semibold text-slate-800">
              {it.record_count}
            </div>
            <div className="text-xs text-slate-400">
              records · <span className="font-mono">{it.table}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="card overflow-hidden">
        <div className="flex gap-1 border-b border-slate-200 px-3 pt-3">
          {(Object.keys(SOURCES) as SourceKey[]).map((key) => (
            <button
              key={key}
              onClick={() => setActive(key)}
              className={`rounded-t-md px-3 py-2 text-sm font-medium capitalize ${
                active === key
                  ? "border border-b-0 border-slate-200 bg-white text-brand-700"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {key}
            </button>
          ))}
        </div>
        {source.isLoading ? (
          <Loading />
        ) : (
          <DataTable rows={source.data?.items ?? []} />
        )}
      </div>
    </div>
  );
}
