import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { listAudit } from "@/api/queries";
import { EmptyState, JsonView, Loading } from "@/components/ui";
import { formatDateTime, titleCase } from "@/lib/format";
import type { AuditEvent } from "@/types";

export function AuditPage() {
  const [params, setParams] = useSearchParams();
  const [expanded, setExpanded] = useState<string | null>(null);
  const filters = {
    entity_type: params.get("entity_type") ?? "",
    action: params.get("action") ?? "",
  };

  const query = useQuery({
    queryKey: ["audit", filters],
    queryFn: () => listAudit({ ...filters, limit: 100 }),
  });

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };

  return (
    <div className="space-y-5">
      <div className="card p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div>
            <label className="label">Entity type</label>
            <select
              className="input"
              value={filters.entity_type}
              onChange={(e) => setFilter("entity_type", e.target.value)}
            >
              <option value="">All</option>
              <option value="KycCase">KYC Case</option>
              <option value="Refund">Refund</option>
              <option value="FeatureFlag">Feature Flag</option>
            </select>
          </div>
          <div>
            <label className="label">Action contains</label>
            <input
              className="input"
              value={filters.action}
              onChange={(e) => setFilter("action", e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        {query.isLoading ? (
          <Loading />
        ) : !query.data || query.data.items.length === 0 ? (
          <EmptyState message="No audit events match these filters." />
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50">
              <tr>
                <th className="th">Time</th>
                <th className="th">Actor</th>
                <th className="th">Action</th>
                <th className="th">Entity</th>
                <th className="th">IP</th>
                <th className="th"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {query.data.items.map((e: AuditEvent) => (
                <Fragment key={e.id}>
                  <tr className="hover:bg-slate-50">
                    <td className="td text-slate-500">
                      {formatDateTime(e.created_at)}
                    </td>
                    <td className="td">{e.actor?.name ?? "System"}</td>
                    <td className="td font-medium">{titleCase(e.action)}</td>
                    <td className="td text-slate-500">
                      {e.entity_type} · {e.entity_id.slice(0, 10)}
                    </td>
                    <td className="td text-slate-400">{e.ip_address ?? "—"}</td>
                    <td className="td">
                      <button
                        className="text-xs text-brand-600 hover:underline"
                        onClick={() =>
                          setExpanded(expanded === e.id ? null : e.id)
                        }
                      >
                        {expanded === e.id ? "Hide" : "Details"}
                      </button>
                    </td>
                  </tr>
                  {expanded === e.id && (
                    <tr>
                      <td colSpan={6} className="bg-slate-50 px-3 py-3">
                        <div className="grid gap-3 md:grid-cols-2">
                          <div>
                            <div className="mb-1 text-xs font-semibold text-slate-500">
                              Before
                            </div>
                            <JsonView data={e.before} />
                          </div>
                          <div>
                            <div className="mb-1 text-xs font-semibold text-slate-500">
                              After
                            </div>
                            <JsonView data={e.after} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {query.data && (
        <div className="text-xs text-slate-400">{query.data.total} event(s)</div>
      )}
    </div>
  );
}
