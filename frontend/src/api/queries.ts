import { api, qs } from "@/api/client";
import type {
  FeatureFlag,
  KycCase,
  Overview,
  Paged,
  Payment,
} from "@/types";

// --- Overview ---
export const getOverview = () => api.get<Overview>("/overview");

// --- KYC ---
export interface KycSummary {
  awaiting_review: number;
  high_risk: number;
  oldest_unreviewed_at: string | null;
  reviewed_today: number;
}
export const getKycSummary = () => api.get<KycSummary>("/kyc/summary");
export const listKyc = (params: Record<string, unknown>) =>
  api.get<Paged<KycCase>>(`/kyc${qs(params)}`);
export const getKycCase = (id: string) => api.get<KycCase>(`/kyc/${id}`);

// --- Refunds / Payments ---
export interface PaymentsSummary {
  gross_volume_minor: number;
  refunded_today_minor: number;
  refund_rate: number;
  failed_refunds: number;
}
export const getPaymentsSummary = () =>
  api.get<PaymentsSummary>("/payments/summary");
export const listPayments = (params: Record<string, unknown>) =>
  api.get<Paged<Payment>>(`/payments${qs(params)}`);
export const getPayment = (id: string) => api.get<Payment>(`/payments/${id}`);

// --- Feature flags ---
export const listFlags = (params: Record<string, unknown>) =>
  api.get<Paged<FeatureFlag>>(`/feature-flags${qs(params)}`);
export const getFlag = (id: string) => api.get<FeatureFlag>(`/feature-flags/${id}`);

// --- Integrations ---
export interface IntegrationHealth {
  key: string;
  name: string;
  category: string;
  status: string;
  record_count: number;
  last_synced_at: string | null;
  next_sync_at: string | null;
}
export interface IntegrationsResponse {
  integrations: IntegrationHealth[];
  last_synced_at: string | null;
  next_sync_at: string | null;
  sync_interval_minutes: number;
}
export const listIntegrations = () =>
  api.get<IntegrationsResponse>("/integrations");

export interface PersonaRow {
  inquiry_id: string;
  reference_id: string;
  status: string;
  name: string;
  email: string | null;
  country_code: string | null;
  risk_score: number | null;
  created_at: string | null;
}
export interface StripeRow {
  charge_id: string;
  payment_intent: string | null;
  amount: number;
  amount_refunded: number;
  currency: string;
  status: string;
  customer_email: string | null;
  card_brand: string | null;
  card_last4: string | null;
  created_at: string | null;
}
export const getPersonaRows = () =>
  api.get<{ items: PersonaRow[] }>("/integrations/persona");
export const getStripeRows = () =>
  api.get<{ items: StripeRow[] }>("/integrations/stripe");

export interface SyncCounts {
  created: number;
  updated: number;
  skipped: number;
}
export interface SyncResult {
  result: { persona_kyc: SyncCounts; stripe_payments: SyncCounts };
}
export const runIntegrationSync = () =>
  api.post<SyncResult>("/integrations/sync");
