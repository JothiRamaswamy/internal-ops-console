import { api, qs } from "@/api/client";
import type {
  AuditEvent,
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

// --- Audit ---
export const listAudit = (params: Record<string, unknown>) =>
  api.get<Paged<AuditEvent>>(`/audit-events${qs(params)}`);

// --- Integrations ---
export interface IntegrationSummary {
  key: string;
  name: string;
  category: string;
  table: string;
  record_count: number;
}
export const listIntegrations = () =>
  api.get<{ integrations: IntegrationSummary[] }>("/integrations");
export const getPersona = () =>
  api.get<{ items: Record<string, unknown>[] }>("/integrations/persona");
export const getStripe = () =>
  api.get<{ items: Record<string, unknown>[] }>("/integrations/stripe");
export const getLaunchDarkly = () =>
  api.get<{ items: Record<string, unknown>[] }>("/integrations/launchdarkly");
