import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/auth/AuthContext";
import { titleCase } from "@/lib/format";

export function SignInScreen() {
  const { users, loginAs } = useAuth();
  const [busy, setBusy] = useState<string | null>(null);
  const qc = useQueryClient();

  const signIn = async (id: string) => {
    setBusy(id);
    try {
      await loginAs(id);
      await qc.invalidateQueries();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="card w-full max-w-md p-6">
        <div className="mb-1 flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-600 text-sm font-bold text-white">
            IO
          </div>
          <h1 className="text-lg font-semibold text-slate-800">
            Internal Operations Console
          </h1>
        </div>
        <p className="mb-5 text-sm text-slate-500">
          Development sign-in. Pick a seeded user to explore each role's
          permissions. In production this is replaced by SSO.
        </p>
        <div className="space-y-2">
          {users.map((u) => (
            <button
              key={u.id}
              disabled={busy !== null}
              onClick={() => signIn(u.id)}
              className="flex w-full items-center justify-between rounded-md border border-slate-200 px-4 py-3 text-left hover:border-brand-300 hover:bg-brand-50 disabled:opacity-50"
            >
              <span>
                <span className="block text-sm font-medium text-slate-800">
                  {u.name}
                </span>
                <span className="block text-xs text-slate-400">{u.email}</span>
              </span>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
                {titleCase(u.role)}
              </span>
            </button>
          ))}
          {users.length === 0 && (
            <p className="text-sm text-red-600">
              No users found. Is the backend running and seeded?
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
