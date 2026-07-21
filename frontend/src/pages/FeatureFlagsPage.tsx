import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";

import { api, ApiRequestError } from "@/api/client";
import { listFlags } from "@/api/queries";
import { useAuth } from "@/auth/AuthContext";
import { Dialog } from "@/components/Dialog";
import { useToast } from "@/components/Toast";
import { EmptyState, Loading } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import type { FeatureFlag, FlagValue } from "@/types";

function EnvValue({ v }: { v: FlagValue | undefined }) {
  if (!v) return <span className="text-slate-300">—</span>;
  const on = v.value?.enabled === true;
  const pct = v.value?.rollout_percentage ?? 0;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium ${
        on ? "text-green-700" : "text-slate-400"
      }`}
    >
      <span
        className={`h-2 w-2 rounded-full ${on ? "bg-green-500" : "bg-slate-300"}`}
      />
      {on ? `On · ${pct}%` : "Off"}
    </span>
  );
}

export function FeatureFlagsPage() {
  const [params, setParams] = useSearchParams();
  const { can } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ key: "", description: "", owner: "", tags: "" });

  const filters = {
    q: params.get("q") ?? "",
    owner: params.get("owner") ?? "",
    tag: params.get("tag") ?? "",
    archived_only: params.get("archived_only") ?? "",
  };

  const create = useMutation({
    mutationFn: () =>
      api.post<FeatureFlag>("/feature-flags", {
        key: form.key.trim(),
        description: form.description,
        owner: form.owner || null,
        tags: form.tags
          ? form.tags.split(",").map((t) => t.trim()).filter(Boolean)
          : [],
      }),
    onSuccess: (flag) => {
      toast.success("Feature flag created.");
      setCreateOpen(false);
      setForm({ key: "", description: "", owner: "", tags: "" });
      qc.invalidateQueries({ queryKey: ["flags"] });
      navigate(`/feature-flags/${flag.id}`);
    },
    onError: (e) =>
      toast.error(e instanceof ApiRequestError ? e.message : "Create failed"),
  });

  const query = useQuery({
    queryKey: ["flags", filters],
    queryFn: () =>
      listFlags({
        q: filters.q,
        owner: filters.owner,
        tag: filters.tag,
        archived_only: filters.archived_only === "true",
      }),
  });

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };
  const hasFilters = Object.values(filters).some(Boolean);

  const canCreate = can("feature_flag:write_nonprod");

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Manage rollout of features across environments. Toggle, set a rollout
          percentage, and add targeting filters per environment.
        </p>
        <button
          className="btn-primary"
          disabled={!canCreate}
          onClick={() => setCreateOpen(true)}
        >
          <Plus className="h-4 w-4" /> New flag
        </button>
      </div>

      <div className="card p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div>
            <label className="label">Search</label>
            <input
              className="input"
              placeholder="Key or description"
              value={filters.q}
              onChange={(e) => setFilter("q", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Owner</label>
            <input
              className="input"
              value={filters.owner}
              onChange={(e) => setFilter("owner", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Tag</label>
            <input
              className="input"
              value={filters.tag}
              onChange={(e) => setFilter("tag", e.target.value)}
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={filters.archived_only === "true"}
                onChange={(e) =>
                  setFilter("archived_only", e.target.checked ? "true" : "")
                }
              />
              Archived only
            </label>
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
          <EmptyState message="No feature flags match these filters." />
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50">
              <tr>
                <th className="th">Flag key</th>
                <th className="th">Description</th>
                <th className="th">Dev</th>
                <th className="th">Staging</th>
                <th className="th">Prod</th>
                <th className="th">Owner</th>
                <th className="th">Updated</th>
                <th className="th">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {query.data.items.map((f) => (
                <tr key={f.id} className="hover:bg-slate-50">
                  <td className="td">
                    <Link
                      to={`/feature-flags/${f.id}`}
                      className="font-mono text-xs font-medium text-brand-600 hover:underline"
                    >
                      {f.key}
                    </Link>
                  </td>
                  <td className="td text-slate-600">{f.description}</td>
                  <td className="td">
                    <EnvValue v={f.values.DEVELOPMENT} />
                  </td>
                  <td className="td">
                    <EnvValue v={f.values.STAGING} />
                  </td>
                  <td className="td">
                    <EnvValue v={f.values.PRODUCTION} />
                  </td>
                  <td className="td text-slate-500">{f.owner}</td>
                  <td className="td text-slate-500">
                    {formatDateTime(f.updated_at)}
                  </td>
                  <td className="td">
                    {f.is_archived ? (
                      <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-600">
                        Archived
                      </span>
                    ) : (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
                        Active
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Dialog
        open={createOpen}
        title="Create feature flag"
        onClose={() => setCreateOpen(false)}
        footer={
          <>
            <button className="btn-secondary" onClick={() => setCreateOpen(false)}>
              Cancel
            </button>
            <button
              className="btn-primary"
              disabled={!form.key.trim() || create.isPending}
              onClick={() => create.mutate()}
            >
              Create flag
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">Key (immutable)</label>
            <input
              className="input font-mono"
              placeholder="new-checkout-flow"
              value={form.key}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  key: e.target.value.replace(/[^a-zA-Z0-9-_]/g, "-").toLowerCase(),
                }))
              }
            />
          </div>
          <div>
            <label className="label">Description</label>
            <input
              className="input"
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Owner</label>
              <input
                className="input"
                placeholder="team name"
                value={form.owner}
                onChange={(e) => setForm((f) => ({ ...f, owner: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Tags (comma-separated)</label>
              <input
                className="input"
                placeholder="billing, beta"
                value={form.tags}
                onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
              />
            </div>
          </div>
          <p className="text-xs text-slate-400">
            New flags start disabled in all environments. Configure rollout and
            targeting after creating.
          </p>
        </div>
      </Dialog>
    </div>
  );
}
