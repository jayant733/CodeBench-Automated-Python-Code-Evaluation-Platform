/**
 * Generated from packages/shared-types/openapi.json.
 * Do not edit directly; run `npm run contracts:generate`.
 */

export interface EvaluationReport {
  evaluation_id: string;
  feedback: FeedbackItem[];
  hidden_test_summary: HiddenTestSummary;
  passed: boolean;
  runtime_ms: number;
  score: number;
  score_breakdown: ScoreBreakdown;
  status: "completed";
  stderr: string;
  stdout: string;
  summary: string;
  task_id: string;
  visible_tests: TestResult[];
}

export interface EvaluationRequest {
  source_code: string;
  task_id: string;
}

export interface Example {
  explanation?: string | null;
  input: string;
  output: string;
}

export interface FeedbackItem {
  code: string;
  message: string;
  severity: "info" | "warning" | "error";
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface HiddenTestSummary {
  failed: number;
  passed: number;
  total: number;
}

export interface PublicTask {
  category: string;
  difficulty: "introductory" | "intermediate" | "advanced";
  examples: Example[];
  function_name: string;
  hidden_test_count: number;
  id: string;
  instructions: string;
  memory_limit_mb: number;
  signature: string;
  starter_code: string;
  summary: string;
  time_limit_seconds: number;
  title: string;
  visible_test_count: number;
  visible_tests: PublicTestCase[];
}

export interface PublicTestCase {
  expected?: unknown;
  expected_exception?: string | null;
  id: string;
  input: Record<string, unknown>;
  name: string;
}

export interface ScoreBreakdown {
  correctness: number;
  execution_signals: number;
  instruction_adherence: number;
}

export interface TaskSummary {
  category: string;
  difficulty: "introductory" | "intermediate" | "advanced";
  hidden_test_count: number;
  id: string;
  summary: string;
  title: string;
  visible_test_count: number;
}

export interface TestResult {
  id: string;
  message?: string | null;
  name: string;
  runtime_ms: number;
  status: "passed" | "failed" | "error";
}

export interface ValidationError {
  ctx?: Record<string, unknown>;
  input?: unknown;
  loc: (string | number)[];
  msg: string;
  type: string;
}

export type Difficulty = TaskSummary["difficulty"];
export type TestStatus = TestResult["status"];
