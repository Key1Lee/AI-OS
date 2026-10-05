export type Status = 'pass' | 'warning' | 'fail' | 'unknown';
export type Cardinality = '1:1' | '1:N' | 'N:1' | 'N:N' | 'unknown';
export type Row = Record<string, unknown>;
export interface Grain {
  declared: string | null; label: string; evidence: string; status: Status;
  classification: 'declared' | 'inference' | 'unknown';
}
export interface Column { name: string; data_type: string; nullable: boolean; description: string }
export interface TestResult { id: string; name: string; status: Status; expected: unknown; actual: unknown; evidence: string }
export interface Model {
  id: string; name: string; layer: string; why: string; grain: Grain; primary_key: string[];
  columns: Column[]; row_count: number | null; rows: Row[]; parents: string[];
  materialization: string; sql: string | null; status: Status; tests: TestResult[];
}
export interface Step {
  id: string; input_model: string; output_model: string; operation: string; why: string;
  input_grain: string; output_grain: string; input_rows: number | null; output_rows: number | null;
  columns_added: string[]; columns_removed: string[]; columns_renamed: Record<string, string>;
  filters: string[]; joins: string[]; aggregations: string[]; windows: string[]; tests: TestResult[];
}
export interface Metric {
  name: string; description: string; measure: string; aggregation: 'SUM' | 'AVG' | 'COUNT';
  time_dimension: string; filters: string[]; dimensions: string[]; grain: string; owner: string;
  currency: string; value: string | null; expected_value: string; status: Status; evidence: string;
}
export interface Scenario {
  contract_version: string; id: string; title: string; business_question: string;
  business_definition: string; sources: Model[]; planned_models: Model[];
  relationships: { id: string; left_model: string; right_model: string; left_key: string; right_key: string; expected: Cardinality; description: string }[];
  transformations: Step[]; reference_sql: Record<string, string>;
  fact_contract: { grain: string; primary_key: string[]; columns: Column[]; owner: string; semantic_meaning: string };
  expected_revenue: string; planned_metric: Metric;
}
export interface BuildRequest { source_grain: string; grain: string; primary_key: string[]; strategy: 'safe' | 'fanout'; sql?: string }
export interface BuildResult {
  staging: Model; fact: Model; metric: Metric; transformations: Step[]; inputs: Model[];
  evaluation: { status: Status; sql_valid: boolean; output_matches_expected: boolean;
    grain: Grain; primary_key: { unique: boolean; not_null: boolean }; tests: TestResult[];
    warnings: string[]; explanation: string; explanation_source: string; performance_notes: string[] };
}
export interface StageResult { model: Model; transformation: Step }
export interface GrainResult { model: Model; tests: TestResult[]; status: Status }
export interface JoinRequest {
  left_table: string; right_table: string; left_key: string; right_key: string;
  kind: 'left' | 'inner'; aggregate_right: boolean; expected_cardinality: Cardinality; expected_rows: number;
}
export interface JoinResult {
  left_table: string; right_table: string; left_rows: number; right_rows: number;
  right_rows_after: number; expected_cardinality: Cardinality; actual_cardinality: Cardinality;
  expected_rows: number; calculated_rows: number; actual_rows: number; unmatched_left_rows: number;
  null_left_keys: number; null_right_keys: number; left_grain: string; right_grain: string;
  resulting_grain: Grain; fanout: boolean; baseline_amount: string | null; joined_amount: string | null;
  currency: string | null; trace: { key: unknown; left_rows: number; right_rows: number; output_rows: number;
    repeated: boolean; order_amount: string | null; contribution: string | null }[];
  rows: Row[]; sql: string; tests: TestResult[]; explanation: string;
}
