export type CircuitState = 'CLOSED' | 'HALF-OPEN' | 'OPEN';
export type RunState = 'QUEUED' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'STALE';
export type ActionType = 'FILE_WRITE' | 'COMMAND_EXEC' | 'EXTERNAL_CALL' | 'DEPENDENCY_UPDATE';

export interface StatsSummary {
  total_sessions: number;
  sessions_trend_pct: number;
  verified_compliance_pct: number;
  verified_cycles_count: number;
  action_required_count: number;
  compute_expenditure_usd: number;
  compute_tokens_k: number;
  budget_burn_pct: number;
}

export interface ProviderHealth {
  id: string;
  slot_number: number;
  provider_name: string;
  model_id: string;
  role: string;
  circuit_state: CircuitState;
  latency_ms: number;
  error_rate_pct: number;
  token_volume: number;
  description: string;
  tags: string[];
}

export interface RunItem {
  id: string;
  run_number: number;
  status: RunState;
  repository: string;
  pr_number: number;
  pr_title: string;
  commit_sha: string;
  trigger_event: string;
  policy_version: string;
  steps_completed: number;
  total_steps: number;
  cost_usd: number;
  tokens_total: number;
  duration_seconds: number;
  started_at: string;
  recorded_at_relative: string;
  agent_name: string;
  risk_score: number;
  milestones_count?: number;
}

export interface StepExplanation {
  task: string;
  subsystem: string;
  governance_role: string;
}

export interface DecisionTraceStep {
  step_number: number;
  phase: string;
  title: string;
  status: 'COMPLETED' | 'PAUSED' | 'FAILED' | 'PENDING';
  duration_ms: number;
  risk_score: number;
  summary: string;
  policy_rule?: string;
  action_type?: string;
  details?: {
    files_checked?: string[];
    ast_nodes_scanned?: number;
    proposed_diff?: string;
    diff_unified?: string;
    target_path?: string;
    reason?: string;
    error?: string;
    message?: string;
    capability?: string;
    action?: string;
    decision?: string;
    success?: boolean;
    raw_payload?: Record<string, any>;
  };
  explanation?: StepExplanation;
}

export interface RunDetail extends RunItem {
  branch: string;
  head_sha: string;
  ed25519_verified: boolean;
  policy_spec: string;
  policy_sha: string;
  steps: DecisionTraceStep[];
}

export interface SystemLogItem {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
  source: string;
  api_name?: string;
  message: string;
  task_progress?: string;
  status: 'PASS' | 'FAIL' | 'WAITING' | 'RUNNING';
  commit_sha?: string;
  pr_number?: number;
  repo?: string;
  run_id?: string;
  latency_ms: number;
  extra_info?: Record<string, any>;
  expires_at: string;
}

export interface PaginatedLogsResponse {
  items: SystemLogItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApprovalRequest {
  id: string;
  display_id?: string;
  run_id: string;
  requested_at: string;
  agent_name: string;
  target_file: string;
  action_type: string;
  action_description: string;
  repository: string;
  pr_number: number;
  branch: string;
  risk_score: number;
  evaluation_result: 'CRITICAL_STOP' | 'WARNING' | 'STANDARD_REVIEW';
  triggered_invariant: string;
  invariant_condition: string;
  blast_radius_desc: string;
  token_anomaly_desc: string;
  diff_additions: number;
  diff_deletions: number;
  diff_lines: Array<{
    type: 'add' | 'delete' | 'context';
    oldLine?: number;
    newLine?: number;
    content: string;
  }>;
}

export interface PolicyDefinition {
  schema_version: string;
  id: string;
  jurisdiction: string;
  enforcement_mode: string;
  yaml_content: string;
  rego_content: string;
  eval_p99_ms: number;
  invariants_count: number;
  active_bundles_count: number;
}

export interface HourlyAnalyticsItem {
  time: string;
  completed: number;
  paused: number;
  failed: number;
  active: boolean;
}

export interface OPASystemHealth {
  status: string;
  endpoint: string;
  memory_rss_mb: number;
  cache_hit_rate_pct: number;
  avg_eval_latency_ms: number;
  active_invariants_count: number;
  bundles_loaded: number;
  test_suite: {
    total: number;
    passed: number;
    failed: number;
    all_passing: boolean;
    tests: Array<{ name: string; passed: boolean }>;
  };
}

export interface CircuitTuning {
  failure_threshold_pct: number;
  consecutive_timeouts: number;
  cooldown_period_seconds: number;
  probes_required: number;
  auto_fallback_enabled: boolean;
}

export interface ProviderConfigItem {
  name: string;
  display_name: string;
  models: string[];
  selected_model: string;
  role: 'primary' | 'fallback' | 'specialist';
  task_types: string[];
  is_active: boolean;
}

export interface LLMProvidersConfig {
  default_primary: string;
  default_fallback: string;
  routing_strategy: string;
  providers: ProviderConfigItem[];
}
