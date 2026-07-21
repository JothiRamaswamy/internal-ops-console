import { Route, Routes } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { AppShell } from "@/components/AppShell";
import { SignInScreen } from "@/pages/SignInScreen";
import { OverviewPage } from "@/pages/OverviewPage";
import { KycListPage } from "@/pages/KycListPage";
import { KycDetailPage } from "@/pages/KycDetailPage";
import { RefundsListPage } from "@/pages/RefundsListPage";
import { PaymentDetailPage } from "@/pages/PaymentDetailPage";
import { FeatureFlagsPage } from "@/pages/FeatureFlagsPage";
import { FeatureFlagDetailPage } from "@/pages/FeatureFlagDetailPage";
import { IntegrationsPage } from "@/pages/IntegrationsPage";

export default function App() {
  const { me, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-400">
        Loading…
      </div>
    );
  }

  if (!me) return <SignInScreen />;

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<OverviewPage />} />
        <Route path="kyc" element={<KycListPage />} />
        <Route path="kyc/:id" element={<KycDetailPage />} />
        <Route path="refunds" element={<RefundsListPage />} />
        <Route path="refunds/:id" element={<PaymentDetailPage />} />
        <Route path="feature-flags" element={<FeatureFlagsPage />} />
        <Route path="feature-flags/:id" element={<FeatureFlagDetailPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="*" element={<OverviewPage />} />
      </Route>
    </Routes>
  );
}
