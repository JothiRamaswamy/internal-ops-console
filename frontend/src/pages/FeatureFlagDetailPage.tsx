import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";

import { api, ApiRequestError } from "@/api/client";
import { getFlag } from "@/api/queries";
import { useAuth } from "@/auth/AuthContext";
import { Dialog } from "@/components/Dialog";
import { useToast } from "@/components/Toast";
import { CopyId, Loading } from "@/components/ui";
import { formatDateTime, titleCase } from "@/lib/format";
import type { FeatureFlag, FlagConfig } from "@/types";

const ENVS = ["DEVELOPMENT", "STAGING", "PRODUCTION"] as const;
const OPERATORS = [
  ["equals", "equals"],
  ["not_equals", "does not equal"],
  ["contains", "contains"],
  ["in", "is one of (comma-sep)"],
];

function permFor(env: string) {
  return env === "PRODUCTION"
    ? "feature_flag:write_prod"
    : "feature_flag:write_nonprod";
}

function emptyConfig(): FlagConfig {
  return { enabled: false, rollout_percentage: 0, filters: [] };
}

interface PendingSave {
  env: string;
  config: FlagConfig;
  version: number;
}

function EnvEditor({
  env,
  config,
  version,
  updatedBy,
  updatedAt,
  editable,
  saving,
  onSave,
}: {
  env: string;
  config: FlagConfig;
  version: number;
  updatedBy?: string;
  updatedAt?: string;
  editable: boolean;
  saving: boolean;
  onSave: (env: string, config: FlagConfig, version: number) => void;
}) {
  const [draft, setDraft] = useState<FlagConfig>(config);

  useEffect(() => {
    setDraft(config);
  }, [config, version]);

  const dirty = JSON.stringify(draft) !== JSON.stringify(config);

  const update = (patch: Partial<FlagConfig>) =>
    setDraft((d) => ({ ...d, ...patch }));

  const setFilter = (i: number, key: keyof FlagConfig["filters"][number], val: string) =>
    setDraft((d) => ({
      ...d,
      filters: d.filters.map((f, idx) => (idx === i ? { ...f, [key]: val } : f)),
    }));

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-800">
          {titleCase(env)}
        </span>
        <span className="text-xs text-slate-400">v{version}</span>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span
          className={`text-sm font-semibold ${
            draft.enabled ? "text-green-600" : "text-slate-400"
          }`}
        >
          {draft.enabled ? "Enabled" : "Disabled"}
        </span>
        <button
          role="switch"
          aria-checked={draft.enabled}
          disabled={!editable}
          onClick={() => update({ enabled: !draft.enabled })}
          className={`relative h-6 w-11 rounded-full transition ${
            draft.enabled ? "bg-green-500" : "bg-slate-300"
          } disabled:opacity-40`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${
              draft.enabled ? "left-[22px]" : "left-0.5"
            }`}
          />
        </button>
      </div>

      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between">
          <label className="label mb-0">Rollout percentage</label>
          <span className="text-sm font-medium text-slate-700">
            {draft.rollout_percentage}%
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          disabled={!editable || !draft.enabled}
          value={draft.rollout_percentage}
          onChange={(e) =>
            update({ rollout_percentage: Number(e.target.value) })
          }
          className="w-full accent-brand-600 disabled:opacity-40"
        />
      </div>

      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between">
          <label className="label mb-0">Targeting filters</label>
          {editable && (
            <button
              className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"
              onClick={() =>
                update({
                  filters: [
                    ...draft.filters,
                    { property: "", operator: "equals", value: "" },
                  ],
                })
              }
            >
              <Plus className="h-3 w-3" /> Add
            </button>
          )}
        </div>
        {draft.filters.length === 0 && (
          <p className="text-xs text-slate-400">
            No filters — applies to all users (subject to rollout %).
          </p>
        )}
        <div className="space-y-2">
          {draft.filters.map((f, i) => (
            <div key={i} className="flex items-center gap-1">
              <input
                className="input py-1 text-xs"
                placeholder="property"
                disabled={!editable}
                value={f.property}
                onChange={(e) => setFilter(i, "property", e.target.value)}
              />
              <select
                className="input py-1 text-xs"
                disabled={!editable}
                value={f.operator}
                onChange={(e) => setFilter(i, "operator", e.target.value)}
              >
                {OPERATORS.map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
              <input
                className="input py-1 text-xs"
                placeholder="value"
                disabled={!editable}
                value={String(f.value)}
                onChange={(e) => setFilter(i, "value", e.target.value)}
              />
              {editable && (
                <button
                  className="shrink-0 text-slate-400 hover:text-red-600"
                  onClick={() =>
                    update({
                      filters: draft.filters.filter((_, idx) => idx !== i),
                    })
                  }
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-3 space-y-1 text-xs text-slate-400">
        <div>Last changed by {updatedBy ?? "—"}</div>
        <div>{formatDateTime(updatedAt)}</div>
      </div>

      {editable && (
        <div className="mt-3 flex justify-end">
          <button
            className="btn-primary"
            disabled={!dirty || saving}
            onClick={() => onSave(env, draft, version)}
          >
            Save {env === "PRODUCTION" ? "to production" : "changes"}
          </button>
        </div>
      )}
    </div>
  );
}

interface EvalResult {
  flag_key: string;
  environment: string;
  enabled: boolean;
  reason: string;
}

function FlagEvaluator({ flagId }: { flagId: string }) {
  const [env, setEnv] = useState<string>("PRODUCTION");
  const [contextText, setContextText] = useState(
    '{\n  "distinct_id": "user-123",\n  "plan": "enterprise"\n}',
  );
  const [jsonError, setJsonError] = useState<string | null>(null);

  const evaluate = useMutation({
    mutationFn: (payload: { environment: string; context: unknown }) =>
      api.post<EvalResult>(`/feature-flags/${flagId}/evaluate`, payload),
  });

  const run = () => {
    let context: unknown;
    try {
      context = JSON.parse(contextText);
    } catch {
      setJsonError("Context must be valid JSON.");
      return;
    }
    if (typeof context !== "object" || context === null || Array.isArray(context)) {
      setJsonError("Context must be a JSON object.");
      return;
    }
    setJsonError(null);
    evaluate.mutate({ environment: env, context });
  };

  const result = evaluate.data;

  return (
    <div className="card p-4">
      <h3 className="text-sm font-semibold text-slate-800">
        Evaluate (SDK preview)
      </h3>
      <p className="mt-1 text-xs text-slate-500">
        Runs the same evaluation logic the SDK uses in application code: applies
        the environment&apos;s targeting filters and rollout % to a context JSON.
      </p>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div>
          <label className="label">Environment</label>
          <select
            className="input"
            value={env}
            onChange={(e) => setEnv(e.target.value)}
          >
            {ENVS.map((e) => (
              <option key={e} value={e}>
                {titleCase(e)}
              </option>
            ))}
          </select>
          <label className="label mt-3">Context (JSON)</label>
          <textarea
            className="input font-mono text-xs"
            rows={7}
            value={contextText}
            onChange={(e) => setContextText(e.target.value)}
            spellCheck={false}
          />
          {jsonError && (
            <p className="mt-1 text-xs text-red-500">{jsonError}</p>
          )}
          <button
            className="btn-primary mt-3"
            disabled={evaluate.isPending}
            onClick={run}
          >
            {evaluate.isPending ? "Evaluating…" : "Evaluate"}
          </button>
        </div>

        <div>
          <label className="label">Result</label>
          {result ? (
            <div className="space-y-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  result.enabled
                    ? "bg-green-100 text-green-700"
                    : "bg-slate-200 text-slate-600"
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    result.enabled ? "bg-green-500" : "bg-slate-400"
                  }`}
                />
                {result.enabled ? "ON — true" : "OFF — false"}
              </span>
              <p className="text-xs text-slate-500">{result.reason}</p>
            </div>
          ) : evaluate.isError ? (
            <p className="text-xs text-red-500">
              {evaluate.error instanceof ApiRequestError
                ? evaluate.error.message
                : "Evaluation failed."}
            </p>
          ) : (
            <p className="text-xs text-slate-400">
              Enter a context and evaluate to see the result.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function FeatureFlagDetailPage() {
  const { id = "" } = useParams();
  const { can } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();

  const [pending, setPending] = useState<PendingSave | null>(null);
  const [reason, setReason] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["flag", id],
    queryFn: () => getFlag(id),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["flag", id] });
    qc.invalidateQueries({ queryKey: ["flags"] });
    qc.invalidateQueries({ queryKey: ["overview"] });
  };

  const setValue = useMutation({
    mutationFn: (payload: {
      environment: string;
      value: FlagConfig;
      expected_version: number;
      reason?: string;
    }) => api.post<FeatureFlag>(`/feature-flags/${id}/value`, payload),
    onSuccess: () => {
      toast.success("Flag updated.");
      setPending(null);
      setReason("");
      invalidate();
    },
    onError: (e) =>
      toast.error(e instanceof ApiRequestError ? e.message : "Update failed"),
  });

  const archive = useMutation({
    mutationFn: (archiveIt: boolean) =>
      api.post<FeatureFlag>(
        `/feature-flags/${id}/${archiveIt ? "archive" : "restore"}`,
      ),
    onSuccess: () => {
      toast.success("Flag updated.");
      invalidate();
    },
    onError: (e) =>
      toast.error(e instanceof ApiRequestError ? e.message : "Update failed"),
  });

  if (isLoading || !data) return <Loading />;

  const onSave = (env: string, config: FlagConfig, version: number) => {
    if (env === "PRODUCTION") {
      setPending({ env, config, version });
    } else {
      setValue.mutate({
        environment: env,
        value: config,
        expected_version: version,
      });
    }
  };

  return (
    <div className="space-y-5">
      <Link
        to="/feature-flags"
        className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> Back to flags
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-mono text-xl font-semibold text-slate-800">
            {data.key}
          </h2>
          <p className="mt-1 text-sm text-slate-500">{data.description}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {data.type}
            </span>
            <span className="text-xs text-slate-400">Owner: {data.owner}</span>
            {data.tags.map((t) => (
              <span
                key={t}
                className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
        {can("feature_flag:write_prod") &&
          (data.is_archived ? (
            <button
              className="btn-secondary"
              onClick={() => archive.mutate(false)}
            >
              Restore flag
            </button>
          ) : (
            <button className="btn-secondary" onClick={() => archive.mutate(true)}>
              Archive flag
            </button>
          ))}
      </div>

      {data.is_archived && (
        <div className="rounded-md bg-slate-100 px-4 py-2 text-sm text-slate-600">
          This flag is archived and cannot be modified until restored.
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {ENVS.map((env) => {
          const v = data.values[env];
          const editable = can(permFor(env)) && !data.is_archived;
          return (
            <EnvEditor
              key={env}
              env={env}
              config={v?.value ?? emptyConfig()}
              version={v?.version ?? 1}
              updatedBy={v?.updated_by?.name}
              updatedAt={v?.updated_at}
              editable={editable}
              saving={setValue.isPending}
              onSave={onSave}
            />
          );
        })}
      </div>

      <FlagEvaluator flagId={id} />

      <div className="card overflow-hidden">
        <h3 className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800">
          Change history
        </h3>
        {(data.versions ?? []).length === 0 ? (
          <div className="p-6 text-center text-sm text-slate-400">
            No changes yet.
          </div>
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50">
              <tr>
                <th className="th">Env</th>
                <th className="th">Version</th>
                <th className="th">Reason</th>
                <th className="th">By</th>
                <th className="th">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(data.versions ?? []).map((v) => (
                <tr key={v.id}>
                  <td className="td">{titleCase(v.environment)}</td>
                  <td className="td">v{v.version}</td>
                  <td className="td text-slate-500">{v.reason || "—"}</td>
                  <td className="td">{v.changed_by?.name}</td>
                  <td className="td text-slate-500">
                    {formatDateTime(v.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card p-4 text-sm">
        Flag ID: <CopyId value={data.id} />
        <span className="ml-3 text-slate-400">
          Archived: {data.archived_at ? formatDateTime(data.archived_at) : "No"}
        </span>
      </div>

      <Dialog
        open={pending !== null}
        title="Confirm production change"
        onClose={() => setPending(null)}
        footer={
          <>
            <button className="btn-secondary" onClick={() => setPending(null)}>
              Cancel
            </button>
            <button
              className="btn-primary"
              disabled={!reason.trim() || setValue.isPending}
              onClick={() =>
                pending &&
                setValue.mutate({
                  environment: pending.env,
                  value: pending.config,
                  expected_version: pending.version,
                  reason,
                })
              }
            >
              Apply to production
            </button>
          </>
        }
      >
        <p className="mb-3 text-sm text-slate-600">
          You are about to change <strong>{data.key}</strong> in{" "}
          <strong>Production</strong>:{" "}
          {pending?.config.enabled
            ? `enabled at ${pending.config.rollout_percentage}% rollout`
            : "disabled"}
          {pending && pending.config.filters.length > 0
            ? ` with ${pending.config.filters.length} targeting filter(s)`
            : ""}
          .
        </p>
        <label className="label">Change reason (required)</label>
        <textarea
          className="input"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why is this production change being made?"
        />
      </Dialog>
    </div>
  );
}
