import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { api } from "@/api/client";
import { ApiRequestError } from "@/api/client";
import { getKycCase } from "@/api/queries";
import { useAuth } from "@/auth/AuthContext";
import { Dialog } from "@/components/Dialog";
import { useToast } from "@/components/Toast";
import {
  CopyId,
  JsonView,
  Loading,
  StatusBadge,
} from "@/components/ui";
import { formatDate, formatDateTime, titleCase } from "@/lib/format";
import type { KycCase } from "@/types";

const REJECT_REASONS = [
  ["DOCUMENT_UNVERIFIABLE", "Document could not be verified"],
  ["IDENTITY_MISMATCH", "Identity mismatch"],
  ["SUSPECTED_FRAUD", "Suspected fraud"],
  ["WATCHLIST_MATCH", "Sanctions/watchlist match"],
  ["UNSUPPORTED_COUNTRY", "Unsupported country"],
  ["DUPLICATE_ACCOUNT", "Duplicate account"],
  ["OTHER", "Other"],
];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </div>
      <div className="mt-0.5 text-sm text-slate-800">{value ?? "—"}</div>
    </div>
  );
}

export function KycDetailPage() {
  const { id = "" } = useParams();
  const { can } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();

  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [note, setNote] = useState("");
  const [reason, setReason] = useState(REJECT_REASONS[0][0]);
  const [explanation, setExplanation] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["kyc-case", id],
    queryFn: () => getKycCase(id),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["kyc-case", id] });
    qc.invalidateQueries({ queryKey: ["kyc-list"] });
    qc.invalidateQueries({ queryKey: ["kyc-summary"] });
  };

  const onError = (e: unknown) =>
    toast.error(e instanceof ApiRequestError ? e.message : "Action failed");

  const assign = useMutation({
    mutationFn: () => api.post<KycCase>(`/kyc/${id}/assign`),
    onSuccess: () => {
      toast.success("Case assigned to you.");
      invalidate();
    },
    onError,
  });

  const approve = useMutation({
    mutationFn: () => api.post<KycCase>(`/kyc/${id}/approve`, { note: note || null }),
    onSuccess: () => {
      toast.success("Case approved.");
      setApproveOpen(false);
      setNote("");
      invalidate();
    },
    onError,
  });

  const reject = useMutation({
    mutationFn: () =>
      api.post<KycCase>(`/kyc/${id}/reject`, {
        reason,
        explanation: explanation || null,
      }),
    onSuccess: () => {
      toast.success("Case rejected.");
      setRejectOpen(false);
      setExplanation("");
      invalidate();
    },
    onError,
  });

  const moreInfo = useMutation({
    mutationFn: () =>
      api.post<KycCase>(`/kyc/${id}/request-more-info`, { note: null }),
    onSuccess: () => {
      toast.success("Requested more information.");
      invalidate();
    },
    onError,
  });

  if (isLoading || !data) return <Loading />;

  const canReview = can("kyc:review");
  const isDecidable = data.status === "NEEDS_REVIEW";
  const payload = (data.raw_vendor_payload ?? {}) as Record<string, any>;
  const checks = (payload.checks ?? {}) as Record<string, string>;

  return (
    <div className="space-y-5">
      <Link
        to="/kyc"
        className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> Back to queue
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">
            {data.customer?.full_name}
          </h2>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge value={data.status} />
            <StatusBadge value={data.risk_level} />
            <CopyId value={data.id} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="btn-secondary"
            disabled={!canReview || assign.isPending || data.status === "APPROVED" || data.status === "REJECTED"}
            onClick={() => assign.mutate()}
          >
            Assign to me
          </button>
          <button
            className="btn-secondary"
            disabled={!canReview || !isDecidable || moreInfo.isPending}
            onClick={() => moreInfo.mutate()}
          >
            Request more info
          </button>
          <button
            className="btn-danger"
            disabled={!canReview || !isDecidable}
            onClick={() => setRejectOpen(true)}
          >
            Reject
          </button>
          <button
            className="btn-primary"
            disabled={!canReview || !isDecidable}
            onClick={() => setApproveOpen(true)}
          >
            Approve
          </button>
        </div>
      </div>

      {!canReview && (
        <div className="rounded-md bg-amber-50 px-4 py-2 text-sm text-amber-800">
          Your role can view this case but cannot make review decisions.
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-800">Customer</h3>
          <div className="space-y-3">
            <Field label="Email" value={data.customer?.email} />
            <Field
              label="Date of birth"
              value={formatDate(data.customer?.date_of_birth)}
            />
            <Field label="Country" value={data.country_code} />
            <Field
              label="Customer ID"
              value={data.customer && <CopyId value={data.customer.id} />}
            />
            <Field
              label="Account created"
              value={formatDate(data.customer?.created_at)}
            />
          </div>
        </div>

        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-800">
            Vendor verification
          </h3>
          <div className="space-y-3">
            <Field label="Vendor" value={data.vendor} />
            <Field
              label="Vendor reference"
              value={<CopyId value={data.vendor_reference_id} />}
            />
            <Field label="Risk score" value={data.risk_score} />
            <Field label="Document" value={checks.document ?? "—"} />
            <Field label="Selfie / liveness" value={checks.selfie ?? "—"} />
            <Field label="Watchlist" value={checks.watchlist ?? "—"} />
            <Field label="Address" value={checks.address ?? "—"} />
          </div>
        </div>

        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-800">Documents</h3>
          <div className="grid grid-cols-3 gap-2">
            {["Front of ID", "Back of ID", "Selfie"].map((d) => (
              <div
                key={d}
                className="flex aspect-[3/4] items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 p-2 text-center text-[11px] text-slate-400"
              >
                {d}
                <br />
                (placeholder)
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Real identity documents are never stored in this prototype.
          </p>
          <h3 className="mb-2 mt-4 text-sm font-semibold text-slate-800">
            Decision
          </h3>
          <div className="space-y-2">
            <Field
              label="Reason"
              value={data.decision_reason ? titleCase(data.decision_reason) : "—"}
            />
            <Field label="Note" value={data.decision_note} />
            <Field label="Decided by" value={data.decided_by?.name} />
            <Field label="Decided at" value={formatDateTime(data.decided_at)} />
          </div>
        </div>
      </div>

      <div className="card p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-800">
          Decision history
        </h3>
        <ol className="space-y-2">
          {(data.events ?? []).map((e) => (
            <li key={e.id} className="flex items-start gap-3 text-sm">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-brand-400" />
              <span>
                <span className="font-medium">{titleCase(e.event_type)}</span>
                {e.actor && (
                  <span className="text-slate-500"> by {e.actor.name}</span>
                )}
                <span className="ml-2 text-xs text-slate-400">
                  {formatDateTime(e.created_at)}
                </span>
              </span>
            </li>
          ))}
        </ol>
      </div>

      <details className="card p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-800">
          Raw vendor payload
        </summary>
        <div className="mt-3">
          <JsonView data={data.raw_vendor_payload} />
        </div>
      </details>

      <Dialog
        open={approveOpen}
        title="Approve KYC case"
        onClose={() => setApproveOpen(false)}
        footer={
          <>
            <button className="btn-secondary" onClick={() => setApproveOpen(false)}>
              Cancel
            </button>
            <button
              className="btn-primary"
              disabled={approve.isPending}
              onClick={() => approve.mutate()}
            >
              Confirm approval
            </button>
          </>
        }
      >
        <p className="mb-3 text-sm text-slate-600">
          Approve verification for{" "}
          <strong>{data.customer?.full_name}</strong>?
        </p>
        <label className="label">Optional note</label>
        <textarea
          className="input"
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </Dialog>

      <Dialog
        open={rejectOpen}
        title="Reject KYC case"
        onClose={() => setRejectOpen(false)}
        footer={
          <>
            <button className="btn-secondary" onClick={() => setRejectOpen(false)}>
              Cancel
            </button>
            <button
              className="btn-danger"
              disabled={reject.isPending}
              onClick={() => reject.mutate()}
            >
              Confirm rejection
            </button>
          </>
        }
      >
        <label className="label">Rejection reason (required)</label>
        <select
          className="input mb-3"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        >
          {REJECT_REASONS.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <label className="label">Explanation (optional)</label>
        <textarea
          className="input"
          rows={3}
          value={explanation}
          onChange={(e) => setExplanation(e.target.value)}
        />
      </Dialog>
    </div>
  );
}
