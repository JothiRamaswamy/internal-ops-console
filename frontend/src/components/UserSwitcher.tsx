import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, UserCircle2 } from "lucide-react";

import { useAuth } from "@/auth/AuthContext";
import { titleCase } from "@/lib/format";

export function UserSwitcher() {
  const { me, users, loginAs } = useAuth();
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();

  const switchTo = async (id: string) => {
    await loginAs(id);
    setOpen(false);
    // Refetch everything under the new identity.
    await qc.invalidateQueries();
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-md border border-slate-200 px-2.5 py-1.5 text-sm hover:bg-slate-50"
      >
        <UserCircle2 className="h-5 w-5 text-slate-400" />
        <span className="text-left leading-tight">
          <span className="block font-medium text-slate-700">
            {me?.name ?? "Signed out"}
          </span>
          <span className="block text-xs text-slate-400">
            {me ? titleCase(me.role) : "Pick a user"}
          </span>
        </span>
        <ChevronDown className="h-4 w-4 text-slate-400" />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 z-20 mt-1 w-64 card p-1">
            <div className="px-3 py-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              Switch user (dev only)
            </div>
            {users.map((u) => (
              <button
                key={u.id}
                onClick={() => switchTo(u.id)}
                className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-slate-100 ${
                  me?.id === u.id ? "bg-brand-50" : ""
                }`}
              >
                <span>
                  <span className="block font-medium text-slate-700">
                    {u.name}
                  </span>
                  <span className="block text-xs text-slate-400">
                    {u.email}
                  </span>
                </span>
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                  {titleCase(u.role)}
                </span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
