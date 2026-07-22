import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { api, ApiRequestError } from "@/api/client";
import { getPayment } from "@/api/queries";
import { useAuth } from "@/auth/AuthContext";
import { Dialog } from "@/components/Dialog";
import { useToast } from "@/components/Toast";
import { CopyId, Loading, StatusBadge } from "@/components/ui";
import { formatDateTime, formatMoney, titleCase } from "@/lib/format";
import type { Payment } from "@/types";

const REASONS = [
  ["DUPLICATE_CHARGE", "Duplicate charge"],
  ["NOT_DELIVERED", "Product/service not delivered"],
  ["CUSTOMER_REQUEST", "Customer request"],
  ["FRAUDULENT_CHARGE", "Fraudulent charge"],
  ["BILLING_ERROR", "Billing error"],
  ["GOODWILL", "Goodwill credit"],
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

export function PaymentDetailPage() {
  const { id = "" } = useParams();
  const { can, me } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();

  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"full" | "partial">("full");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState(REASONS[0][0]);
  const [note, setNote] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["payment", id],
    queryFn: () => getPayment(id),
  });

  const refund = useMutation({
    mutationFn: (payload: { amount_minor: number; reason: string; note: string | null }) =>
      api.post<{ payment: Payment }>(`/payments/${id}/refunds`, {
        ...payload,
        idempotency_key: `ui-${id}-${Date.now()}`,
      }),
    onSuccess: (res) => {
      const refunds = res.payment.refunds ?? [];
      const last = refunds[refunds.length - 1];
      if (last?.status === "FAILED") {
        toast.error(`Refund failed: ${last.failure_reason ?? "provider error"}`);
      } else {
        toast.success("Refund issued successfully.");
      }
      setOpen(false);
      setAmount("");
      setNote("");
      qc.invalidateQueries({ queryKey: ["payment", id] });
      qc.invalidateQueries({ queryKey: ["payments-list"] });
      qc.invalidateQueries({ queryKey: ["payments-summary"] });
    },
    onError: (e) =>
      toast.error(e instanceof ApiRequestError ? e.message : "Refund failed"),
  });

  if (isLoading || !data) return <Loading />;

  const remaining = data.remaining_refundable_minor;
  const canRefund = can("refund:create");
  const amountMinor =
    mode === "full" ? remaining : Math.round(parseFloat(amount || "0") * 100);
  const remainingAfter = Math.max(remaining - amountMinor, 0);
  const limit = me?.refund_limit_minor ?? null;

  return (
    <div className="space-y-5">
      <Link
        to="/refunds"
        className="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> Back to payments
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">
            {formatMoney(data.amount_minor, data.currency)}
          </h2>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge value={data.status} />
            <CopyId value={data.id} />
          </div>
        </div>
        <button
          className="btn-primary"
          disabled={!canRefund || !data.refund_allowed}
          onClick={() => {
            setMode("full");
            setOpen(true);
          }}
        >
          Issue refund
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-800">Payment</h3>
          <div className="space-y-3">
            <Field label="Provider" value={data.provider} />
            <Field
              label="Provider payment ID"
              value={<CopyId value={data.provider_payment_id} />}
            />
            <Field label="Order ID" value={data.order_id} />
            <Field label="Customer" value={data.customer?.full_name} />
            <Field
              label="Method"
              value={`${data.payment_method_brand} ••${data.payment_method_last4}`}
            />
            <Field label="Created" value={formatDateTime(data.created_at)} />
          </div>
        </div>

        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-800">
            Refund eligibility
          </h3>
          <div className="space-y-3">
            <Field
              label="Remaining refundable"
              value={formatMoney(remaining, data.currency)}
            />
            <Field
              label="Refund allowed"
              value={data.refund_allowed ? "Yes" : "No"}
            />
            <Field
              label="Your refund limit"
              value={limit === null ? "No limit" : formatMoney(limit)}
            />
            {!data.refund_allowed && (
              <div className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
                {data.status === "FAILED"
                  ? "Failed payments cannot be refunded."
                  : data.status === "FULLY_REFUNDED"
                    ? "This payment is fully refunded."
                    : data.status === "DISPUTED"
                      ? "Disputed payments cannot be refunded here."
                      : "No refundable balance remaining."}
              </div>
            )}
          </div>
        </div>

        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-800">Totals</h3>
          <div className="space-y-3">
            <Field
              label="Original amount"
              value={formatMoney(data.amount_minor, data.currency)}
            />
            <Field
              label="Refunded"
              value={formatMoney(data.refunded_minor, data.currency)}
            />
            <Field
              label="Currency"
              value={data.currency}
            />
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <h3 className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800">
          Refund history
        </h3>
        {(data.refunds ?? []).length === 0 ? (
          <div className="p-6 text-center text-sm text-slate-400">
            No refunds yet.
          </div>
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-100 bg-slate-50">
              <tr>
                <th className="th">Refund ID</th>
                <th className="th">Amount</th>
                <th className="th">Reason</th>
                <th className="th">Status</th>
                <th className="th">Requested by</th>
                <th className="th">Created</th>
                <th className="th">Provider ref</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(data.refunds ?? []).map((r) => (
                <tr key={r.id}>
                  <td className="td">
                    <CopyId value={r.id} />
                  </td>
                  <td className="td">{formatMoney(r.amount_minor, r.currency)}</td>
                  <td className="td">{titleCase(r.reason)}</td>
                  <td className="td">
                    <StatusBadge value={r.status} />
                    {r.failure_reason && (
                      <div className="text-xs text-red-500">
                        {r.failure_reason}
                      </div>
                    )}
                    {r.status_note && (
                      <div className="text-xs text-slate-500">
                        {r.status_note}
                      </div>
                    )}
                  </td>
                  <td className="td">{r.requested_by?.name}</td>
                  <td className="td text-slate-500">
                    {formatDateTime(r.created_at)}
                  </td>
                  <td className="td text-slate-400">
                    {r.provider_refund_id ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Dialog
        open={open}
        title="Issue refund"
        onClose={() => setOpen(false)}
        footer={
          <>
            <button className="btn-secondary" onClick={() => setOpen(false)}>
              Cancel
            </button>
            <button
              className="btn-primary"
              disabled={
                refund.isPending ||
                amountMinor <= 0 ||
                amountMinor > remaining ||
                (limit !== null && amountMinor > limit)
              }
              onClick={() =>
                refund.mutate({
                  amount_minor: amountMinor,
                  reason,
                  note: note || null,
                })
              }
            >
              Confirm refund of {formatMoney(amountMinor || 0, data.currency)}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="flex gap-2">
            <button
              className={mode === "full" ? "btn-primary" : "btn-secondary"}
              onClick={() => setMode("full")}
            >
              Full ({formatMoney(remaining, data.currency)})
            </button>
            <button
              className={mode === "partial" ? "btn-primary" : "btn-secondary"}
              onClick={() => setMode("partial")}
            >
              Partial
            </button>
          </div>
          {mode === "partial" && (
            <div>
              <label className="label">Amount ({data.currency})</label>
              <input
                className="input"
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </div>
          )}
          <div>
            <label className="label">Reason</label>
            <select
              className="input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            >
              {REASONS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Internal note (optional)</label>
            <textarea
              className="input"
              rows={2}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <div className="rounded-md bg-slate-50 p-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Customer</span>
              <span>{data.customer?.full_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Refund amount</span>
              <span>{formatMoney(amountMinor || 0, data.currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Remaining after</span>
              <span>{formatMoney(remainingAfter, data.currency)}</span>
            </div>
          </div>
          {limit !== null && amountMinor > limit && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
              This exceeds your refund limit of {formatMoney(limit)}.
            </div>
          )}
        </div>
      </Dialog>
    </div>
  );
}
