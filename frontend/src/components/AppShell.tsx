import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  ShieldCheck,
  Receipt,
  Flag,
  ScrollText,
  Plug,
  Search,
} from "lucide-react";

import { UserSwitcher } from "@/components/UserSwitcher";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/kyc", label: "KYC Reviews", icon: ShieldCheck },
  { to: "/refunds", label: "Refunds", icon: Receipt },
  { to: "/feature-flags", label: "Feature Flags", icon: Flag },
  { to: "/audit", label: "Audit Log", icon: ScrollText },
  { to: "/integrations", label: "Integrations", icon: Plug },
];

const TITLES: Record<string, string> = {
  "/": "Overview",
  "/kyc": "KYC Review Queue",
  "/refunds": "Refunds Dashboard",
  "/feature-flags": "Feature Flags",
  "/audit": "Audit Log",
  "/integrations": "Integrations",
};

function currentTitle(pathname: string): string {
  const base = "/" + (pathname.split("/")[1] ?? "");
  return TITLES[base === "/" ? "/" : base] ?? "Internal Ops Console";
}

export function AppShell() {
  const location = useLocation();
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-600 text-sm font-bold text-white">
            IO
          </div>
          <div className="text-sm font-semibold leading-tight text-slate-800">
            Internal Ops
            <div className="text-xs font-normal text-slate-400">Console</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 p-3 text-xs text-slate-400">
          Prototype · v1.0.0
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-slate-800">
              {currentTitle(location.pathname)}
            </h1>
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              Development
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs text-slate-400 md:flex">
              <Search className="h-3.5 w-3.5" />
              Search…
              <kbd className="ml-1 rounded bg-slate-100 px-1">⌘K</kbd>
            </div>
            <UserSwitcher />
          </div>
        </header>
        <main className="min-w-0 flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
