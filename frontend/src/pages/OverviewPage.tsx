import { Link } from "react-router-dom";
import {
  ShieldCheck,
  Receipt,
  Flag,
  Plug,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";

type AppCard = {
  to: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

const APPS: AppCard[] = [
  {
    to: "/kyc",
    label: "KYC Reviews",
    description: "Triage identity-verification cases and approve or reject them.",
    icon: ShieldCheck,
  },
  {
    to: "/refunds",
    label: "Refunds",
    description: "Issue full or partial refunds against payments, with role limits.",
    icon: Receipt,
  },
  {
    to: "/feature-flags",
    label: "Feature Flags",
    description: "Create flags and manage per-environment rollout and targeting.",
    icon: Flag,
  },
  {
    to: "/integrations",
    label: "Integrations",
    description: "Check sync health and browse recently synced vendor rows.",
    icon: Plug,
  },
];

export function OverviewPage() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500">
        Choose an app to get started.
      </p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {APPS.map((app) => (
          <Link
            key={app.to}
            to={app.to}
            className="card group flex flex-col gap-3 p-5 transition hover:border-brand-300 hover:shadow-sm"
          >
            <div className="flex items-center justify-between">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-brand-50 text-brand-700">
                <app.icon className="h-5 w-5" />
              </div>
              <ArrowRight className="h-4 w-4 text-slate-300 transition group-hover:text-brand-500" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-800">
                {app.label}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {app.description}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
