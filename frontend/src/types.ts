export type Role = "ADMIN" | "OPS_REVIEWER" | "SUPPORT_AGENT" | "READ_ONLY";

export interface UserSummary {
  id: string;
  name: string;
  email: string;
  role: Role;
}

export interface Me extends UserSummary {
  permissions: string[];
  refund_limit_minor: number | null;
}

export interface CustomerSummary {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  date_of_birth: string | null;
  country_code: string;
  created_at: string;
}

export interface KycEvent {
  id: string;
  event_type: string;
  actor: UserSummary | null;
  from_status: string | null;
  to_status: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface KycCase {
  id: string;
  customer: CustomerSummary | null;
  vendor: string;
  vendor_reference_id: string;
  status: string;
  risk_level: string;
  risk_score: number | null;
  country_code: string;
  submitted_at: string;
  assigned_reviewer: UserSummary | null;
  decision_reason?: string | null;
  decision_note?: string | null;
  decided_at?: string | null;
  decided_by?: UserSummary | null;
  raw_vendor_payload?: Record<string, unknown>;
  events?: KycEvent[];
}

export interface Refund {
  id: string;
  amount_minor: number;
  currency: string;
  reason: string;
  note: string | null;
  status: string;
  status_note: string | null;
  failure_reason: string | null;
  provider_refund_id: string | null;
  requested_by: UserSummary | null;
  created_at: string;
}

export interface Payment {
  id: string;
  provider: string;
  provider_payment_id: string;
  customer: CustomerSummary | null;
  order_id: string;
  amount_minor: number;
  refunded_minor: number;
  remaining_refundable_minor: number;
  currency: string;
  status: string;
  payment_method_brand: string | null;
  payment_method_last4: string | null;
  created_at: string;
  refunds?: Refund[];
  refund_limit_minor?: number | null;
  refund_allowed?: boolean;
}

export interface FlagFilter {
  property: string;
  operator: string;
  value: string;
}

export interface FlagConfig {
  enabled: boolean;
  rollout_percentage: number;
  filters: FlagFilter[];
}

export interface FlagValue {
  environment: string;
  value: FlagConfig;
  version: number;
  updated_by: UserSummary | null;
  updated_at: string;
}

export interface FlagVersion {
  id: string;
  environment: string;
  previous_value: unknown;
  new_value: unknown;
  version: number;
  reason: string;
  changed_by: UserSummary | null;
  created_at: string;
}

export interface FeatureFlag {
  id: string;
  key: string;
  description: string;
  type: string;
  owner: string;
  tags: string[];
  archived_at: string | null;
  is_archived: boolean;
  values: Record<string, FlagValue>;
  updated_at: string;
  versions?: FlagVersion[];
}

export interface Overview {
  kyc_awaiting_review: number;
  kyc_high_risk: number;
  refund_volume_today_minor: number;
  failed_refunds: number;
  prod_flags_enabled: number;
  prod_flag_changes_last_7d: number;
}

export interface Paged<T> {
  total: number;
  items: T[];
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
