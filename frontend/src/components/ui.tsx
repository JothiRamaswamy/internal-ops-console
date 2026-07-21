import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { titleCase } from "@/lib/format";

const STATUS_STYLES: Record<string, string> = {
  // KYC
  NEEDS_REVIEW: "bg-amber-100 text-amber-800",
  PENDING_VENDOR: "bg-slate-100 text-slate-600",
  REQUESTED_MORE_INFO: "bg-blue-100 text-blue-800",
  APPROVED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  // Risk
  LOW: "bg-green-100 text-green-800",
  MEDIUM: "bg-amber-100 text-amber-800",
  HIGH: "bg-orange-100 text-orange-800",
  CRITICAL: "bg-red-100 text-red-800",
  // Payments
  SUCCEEDED: "bg-green-100 text-green-800",
  PARTIALLY_REFUNDED: "bg-blue-100 text-blue-800",
  FULLY_REFUNDED: "bg-slate-200 text-slate-700",
  DISPUTED: "bg-purple-100 text-purple-800",
  FAILED: "bg-red-100 text-red-800",
  PENDING: "bg-amber-100 text-amber-800",
  CANCELED: "bg-slate-100 text-slate-600",
};

export function StatusBadge({ value }: { value: string }) {
  const cls = STATUS_STYLES[value] ?? "bg-slate-100 text-slate-600";
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {titleCase(value)}
    </span>
  );
}

export function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold text-slate-800">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

export function CopyId({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      className="inline-flex items-center gap-1 font-mono text-xs text-slate-500
        hover:text-slate-800"
      title="Copy ID"
    >
      {value}
      {copied ? (
        <Check className="h-3 w-3 text-green-600" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
    </button>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="p-10 text-center text-sm text-slate-400">{message}</div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="p-10 text-center text-sm text-slate-400">{label}</div>
  );
}

export function JsonView({ data }: { data: unknown }) {
  return (
    <pre className="max-h-96 overflow-auto rounded-md bg-slate-900 p-3 text-xs
      leading-relaxed text-slate-100">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
