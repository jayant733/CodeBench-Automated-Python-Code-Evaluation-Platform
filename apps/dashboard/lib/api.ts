import type {
  EvaluationReport,
  EvaluationRequest,
  PublicTask,
  TaskSummary,
} from "@aices/shared-types";

const API_BASE_URL = process.env.NEXT_PUBLIC_EVALUATOR_URL ?? "http://localhost:8000";

interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
  detail?: string;
}

export class EvaluatorApiError extends Error {
  constructor(
    message: string,
    public readonly code = "request_failed",
  ) {
    super(message);
    this.name = "EvaluatorApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new EvaluatorApiError(
      "The evaluator service is unreachable. Start it and try again.",
      "service_unavailable",
    );
  }

  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      // The fallback below intentionally avoids exposing raw upstream bodies.
    }
    throw new EvaluatorApiError(
      payload.error?.message ?? payload.detail ?? "The evaluator could not complete the request.",
      payload.error?.code,
    );
  }
  return (await response.json()) as T;
}

export function listTasks(): Promise<TaskSummary[]> {
  return request<TaskSummary[]>("/api/tasks");
}

export function getTask(taskId: string): Promise<PublicTask> {
  return request<PublicTask>(`/api/tasks/${encodeURIComponent(taskId)}`);
}

export function evaluate(taskId: string, sourceCode: string): Promise<EvaluationReport> {
  const submission: EvaluationRequest = {
    task_id: taskId,
    source_code: sourceCode,
  };
  return request<EvaluationReport>("/api/evaluations", {
    method: "POST",
    body: JSON.stringify(submission),
  });
}

export interface AgentRunAccepted {
  session_id: string;
  task_id: string;
  status: string;
  max_iterations: number;
}

/** Launches an orchestrated run; the session appears under /sessions while it works. */
export function startAgentSession(taskId: string, maxIterations = 4): Promise<AgentRunAccepted> {
  return request<AgentRunAccepted>("/api/agent/sessions", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId, max_iterations: maxIterations }),
  });
}
