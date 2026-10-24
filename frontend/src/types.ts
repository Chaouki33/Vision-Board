export type Role = "owner" | "editor" | "viewer";

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_admin: boolean;
  must_change_password: boolean;
}

export interface AdminUser extends User {
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  companies: { company_id: number; name: string; role: Role }[];
}

export interface FieldDef {
  code: string;
  label: string;
  type: "date" | "number" | "text";
}

export interface Meta {
  sectors: Record<string, string>;
  sizes: Record<string, string>;
  domains: Record<string, string>;
  sector_domains: Record<string, string[]>;
  fields: Record<string, FieldDef[]>;
}

export interface Company {
  id: number;
  name: string;
  sector: string;
  size: string;
  employees: number | null;
  annual_revenue: number | null;
  city: string | null;
  role: Role;
}

export interface CompanyInput {
  name: string;
  sector: string;
  size: string | null;
  employees: number | null;
  annual_revenue: number | null;
  city: string | null;
  domains?: string[];
}

export interface Member {
  user_id: number;
  email: string;
  full_name: string;
  role: Role;
}

export interface Dataset {
  id: number;
  domain: string;
  name: string;
  source_filename: string;
  file_type: string;
  row_count: number;
  columns: string[];
  mapping: Record<string, string>;
  created_at: string;
}

export interface DatasetDetail extends Dataset {
  preview: Record<string, unknown>[];
  sheets: string[];
}

export interface Recommendation {
  code: string;
  domain: string;
  name: string;
  description: string;
  formula: string;
  unit: string;
  required: string[];
  priority: number;
  available: boolean;
  missing_fields: string[];
  dataset_id: number | null;
  selected: boolean;
  reasons: string[];
}

export interface Recommendations {
  domain: string;
  sector: string;
  size: string;
  suggested_domains: string[];
  datasets: number;
  kpis: Recommendation[];
}

export interface ChartData {
  type: "line" | "bar";
  title: string;
  labels: string[];
  values: number[];
  unit: string;
}

export interface KpiValue {
  code: string;
  name: string;
  description: string;
  formula: string;
  unit: string;
  higher_is_better: boolean | null;
  value: number | null;
  status: "ok" | "warning" | "critical" | null;
  detail: string | null;
  delta: number | null;
  chart: ChartData | null;
  error: string | null;
  rows: number;
}

export interface DashboardData {
  id: number;
  title: string;
  domain: string;
  start: string | null;
  end: string | null;
  data_start: string | null;
  data_end: string | null;
  kpis: KpiValue[];
}

export interface Dashboard {
  id: number;
  domain: string;
  title: string;
  kpi_codes: string[];
  updated_at: string;
}

export interface ReportContent {
  titre: string;
  appreciation_globale: "favorable" | "à surveiller" | "préoccupante";
  synthese: string;
  chiffres_cles: { indicateur: string; valeur: string; commentaire: string }[];
  sections: { titre: string; paragraphes: string[] }[];
  points_forts: string[];
  points_de_vigilance: string[];
  recommandations: { priorite: "haute" | "moyenne" | "basse"; action: string; justification: string; horizon: string }[];
  limites_des_donnees: string[];
  conclusion: string;
}

export interface Report {
  id: number;
  dashboard_id: number | null;
  domain: string;
  title: string;
  status: "pending" | "done" | "error";
  period_start: string | null;
  period_end: string | null;
  instructions: string | null;
  content: ReportContent | null;
  error: string | null;
  model: string | null;
  created_at: string;
  completed_at: string | null;
}
