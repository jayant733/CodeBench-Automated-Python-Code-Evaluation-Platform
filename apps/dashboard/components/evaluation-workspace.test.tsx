import type { EvaluationReport, PublicTask, TaskSummary } from "@aices/shared-types";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EvaluationWorkspace } from "./evaluation-workspace";

const taskSummary: TaskSummary = {
  id: "palindrome-normalization",
  title: "Palindrome normalization",
  summary: "Normalize text.",
  difficulty: "introductory",
  category: "Text processing",
  visible_test_count: 1,
  hidden_test_count: 2,
};

const task: PublicTask = {
  ...taskSummary,
  instructions: "Return whether the normalized value is a palindrome.",
  function_name: "is_normalized_palindrome",
  signature: "def is_normalized_palindrome(value: str) -> bool",
  starter_code: "def is_normalized_palindrome(value: str) -> bool:\n    return True\n",
  time_limit_seconds: 2,
  memory_limit_mb: 128,
  examples: [{ input: '""', output: "True", explanation: null }],
  visible_tests: [
    {
      id: "pal-empty",
      name: "Empty input",
      input: { args: [""] },
      expected: true,
      expected_exception: null,
    },
  ],
};

const report: EvaluationReport = {
  evaluation_id: "eval-1",
  task_id: task.id,
  status: "completed",
  score: 100,
  score_breakdown: {
    correctness: 80,
    instruction_adherence: 10,
    execution_signals: 10,
  },
  passed: true,
  summary: "All 3 tests passed.",
  visible_tests: [
    {
      id: "pal-empty",
      name: "Empty input",
      status: "passed",
      runtime_ms: 1,
      message: null,
    },
  ],
  hidden_test_summary: { passed: 2, failed: 0, total: 2 },
  runtime_ms: 11,
  stdout: "",
  stderr: "",
  feedback: [
    {
      code: "all_tests_passed",
      message: "The submission satisfies every case.",
      severity: "info",
    },
  ],
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("EvaluationWorkspace", () => {
  it("loads a task and renders a structured report after submission", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([taskSummary]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(task), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(report), { status: 200 }));

    render(<EvaluationWorkspace />);

    expect(await screen.findByRole("heading", { name: task.title })).toBeInTheDocument();
    expect(screen.getByLabelText("Python source code")).toHaveValue(task.starter_code);

    await userEvent.click(screen.getByRole("button", { name: "Run evaluation" }));

    expect(await screen.findByText("All 3 tests passed.")).toBeInTheDocument();
    expect(screen.getByLabelText("Score 100 out of 100")).toBeInTheDocument();
    expect(screen.getByText("2/2")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("shows an understandable service error", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("offline"));
    render(<EvaluationWorkspace />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("The evaluator service is unreachable");
    });
    expect(screen.getByRole("button", { name: "Retry connection" })).toBeInTheDocument();
  });
});
