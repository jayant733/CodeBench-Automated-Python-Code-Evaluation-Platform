"use client";

import type { EvaluationReport, PublicTask, TaskSummary, TestResult } from "@aices/shared-types";
import { useCallback, useEffect, useState } from "react";
import { EvaluatorApiError, evaluate, getTask, listTasks } from "../lib/api";

type LoadState = "loading" | "ready" | "error";

function difficultyLabel(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatInput(input: Record<string, unknown>): string {
  return JSON.stringify(input, null, 2);
}

function ResultRow({ result }: { result: TestResult }) {
  return (
    <li className="test-result">
      <span className={`test-icon test-icon--${result.status}`} aria-hidden="true">
        {result.status === "passed" ? "✓" : "×"}
      </span>
      <div>
        <div className="test-result__heading">
          <strong>{result.name}</strong>
          <span>{result.runtime_ms} ms</span>
        </div>
        {result.message ? <p>{result.message}</p> : null}
      </div>
    </li>
  );
}

function EmptyReport() {
  return (
    <section className="report report--empty" aria-label="Evaluation report">
      <span className="report-index">03 / Report</span>
      <div className="empty-mark" aria-hidden="true">
        →
      </div>
      <h2>Evidence lands here.</h2>
      <p>
        Run the prefilled solution to see score composition, visible failures, hidden-test totals,
        runtime, and captured output.
      </p>
    </section>
  );
}

function EvaluationReportView({ report }: { report: EvaluationReport }) {
  return (
    <section className="report" aria-live="polite" aria-label="Evaluation report">
      <div className="report-heading">
        <div>
          <span className="report-index">03 / Report</span>
          <div className={`verdict verdict--${report.passed ? "pass" : "fail"}`}>
            {report.passed ? "Passed" : "Needs work"}
          </div>
        </div>
        <meter
          className="score"
          style={{ "--score": `${report.score * 3.6}deg` } as React.CSSProperties}
          aria-label={`Score ${report.score} out of 100`}
          min={0}
          max={100}
          value={report.score}
        >
          <span>{report.score}</span>
          <small>/ 100</small>
        </meter>
      </div>

      <p className="report-summary">{report.summary}</p>

      <dl className="score-breakdown">
        <div>
          <dt>Correctness</dt>
          <dd>{report.score_breakdown.correctness} / 80</dd>
        </div>
        <div>
          <dt>Instruction fit</dt>
          <dd>{report.score_breakdown.instruction_adherence} / 10</dd>
        </div>
        <div>
          <dt>Execution signals</dt>
          <dd>{report.score_breakdown.execution_signals} / 10</dd>
        </div>
      </dl>

      <div className="hidden-summary">
        <div>
          <span>Hidden tests</span>
          <strong>
            {report.hidden_test_summary.passed}/{report.hidden_test_summary.total}
          </strong>
        </div>
        <div>
          <span>Runtime</span>
          <strong>{report.runtime_ms} ms</strong>
        </div>
      </div>

      <div className="report-section">
        <h3>Visible cases</h3>
        <ul className="test-results">
          {report.visible_tests.map((result) => (
            <ResultRow key={result.id} result={result} />
          ))}
        </ul>
      </div>

      {report.feedback.length ? (
        <div className="report-section">
          <h3>Evaluator feedback</h3>
          <ul className="feedback-list">
            {report.feedback.map((item) => (
              <li key={item.code} data-severity={item.severity}>
                {item.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {report.stdout || report.stderr ? (
        <div className="report-section output-grid">
          <div>
            <h3>stdout</h3>
            <pre>{report.stdout || "—"}</pre>
          </div>
          <div>
            <h3>stderr</h3>
            <pre>{report.stderr || "—"}</pre>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function EvaluationWorkspace() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedTask, setSelectedTask] = useState<PublicTask | null>(null);
  const [sourceCode, setSourceCode] = useState("");
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [taskLoading, setTaskLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectTask = useCallback(async (taskId: string) => {
    setTaskLoading(true);
    setError(null);
    setReport(null);
    try {
      const task = await getTask(taskId);
      setSelectedTask(task);
      setSourceCode(task.starter_code);
    } catch (caught) {
      setError(
        caught instanceof EvaluatorApiError ? caught.message : "The task could not be loaded.",
      );
    } finally {
      setTaskLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const availableTasks = await listTasks();
        if (!active) return;
        setTasks(availableTasks);
        setLoadState("ready");
        const firstTask = availableTasks[0];
        if (firstTask) await selectTask(firstTask.id);
      } catch (caught) {
        if (!active) return;
        setLoadState("error");
        setError(
          caught instanceof EvaluatorApiError
            ? caught.message
            : "The evaluator service could not be reached.",
        );
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [selectTask]);

  async function submit() {
    if (!selectedTask || !sourceCode.trim()) return;
    setSubmitting(true);
    setError(null);
    setReport(null);
    try {
      setReport(await evaluate(selectedTask.id, sourceCode));
    } catch (caught) {
      setError(
        caught instanceof EvaluatorApiError
          ? caught.message
          : "The evaluation could not be completed.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section id="workspace" className="workspace-shell" aria-label="Evaluation workspace">
      {error ? (
        <div className="service-error" role="alert">
          <strong>Evaluator notice</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <div className="workspace-grid">
        <aside className="task-rail" aria-label="Coding tasks">
          <span className="section-index">01 / Tasks</span>
          <div className="task-rail__heading">
            <h2>Challenge set</h2>
            <span>{tasks.length || "—"} tasks</span>
          </div>
          {loadState === "loading" ? <p className="muted">Loading the benchmark catalog…</p> : null}
          {loadState === "error" ? (
            <button type="button" className="quiet-button" onClick={() => window.location.reload()}>
              Retry connection
            </button>
          ) : null}
          <ol className="task-list">
            {tasks.map((task, index) => (
              <li key={task.id}>
                <button
                  type="button"
                  className={selectedTask?.id === task.id ? "is-active" : ""}
                  onClick={() => void selectTask(task.id)}
                  aria-pressed={selectedTask?.id === task.id}
                >
                  <span className="task-number">{String(index + 1).padStart(2, "0")}</span>
                  <span>
                    <strong>{task.title}</strong>
                    <small>
                      {difficultyLabel(task.difficulty)} · {task.category}
                    </small>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </aside>

        <div className="challenge">
          <span className="section-index">02 / Submission</span>
          {selectedTask ? (
            <>
              <div className="challenge-header">
                <div>
                  <div className="tag-row">
                    <span>{selectedTask.category}</span>
                    <span>{difficultyLabel(selectedTask.difficulty)}</span>
                  </div>
                  <h2>{selectedTask.title}</h2>
                  <p>{selectedTask.summary}</p>
                </div>
                <dl className="limits">
                  <div>
                    <dt>Time</dt>
                    <dd>{selectedTask.time_limit_seconds}s</dd>
                  </div>
                  <div>
                    <dt>Memory</dt>
                    <dd>{selectedTask.memory_limit_mb}MB</dd>
                  </div>
                  <div>
                    <dt>Hidden</dt>
                    <dd>{selectedTask.hidden_test_count}</dd>
                  </div>
                </dl>
              </div>

              <div className="brief">
                <h3>Contract</h3>
                <code>{selectedTask.signature}</code>
                <p>{selectedTask.instructions}</p>
              </div>

              <details className="visible-cases">
                <summary>
                  Visible cases <span>{selectedTask.visible_test_count}</span>
                </summary>
                <div className="case-grid">
                  {selectedTask.visible_tests.map((test) => (
                    <article key={test.id}>
                      <strong>{test.name}</strong>
                      <pre>{formatInput(test.input)}</pre>
                      <p>
                        Expected:{" "}
                        <code>{test.expected_exception ?? JSON.stringify(test.expected)}</code>
                      </p>
                    </article>
                  ))}
                </div>
              </details>

              <div className="editor-shell" aria-busy={taskLoading || submitting}>
                <div className="editor-bar">
                  <span>
                    <i aria-hidden="true" />
                    submission.py
                  </span>
                  <button
                    type="button"
                    className="reset-button"
                    onClick={() => setSourceCode(selectedTask.starter_code)}
                    disabled={submitting}
                  >
                    Reset example
                  </button>
                </div>
                <label className="sr-only" htmlFor="source-code">
                  Python source code
                </label>
                <textarea
                  id="source-code"
                  value={sourceCode}
                  onChange={(event) => setSourceCode(event.target.value)}
                  spellCheck={false}
                  autoCapitalize="off"
                  autoCorrect="off"
                  disabled={taskLoading || submitting}
                />
                <div className="editor-actions">
                  <span>Python 3.12 · Docker isolated</span>
                  <button
                    type="button"
                    className="run-button"
                    onClick={() => void submit()}
                    disabled={submitting || taskLoading || !sourceCode.trim()}
                  >
                    <span aria-hidden="true">▶</span>
                    {submitting ? "Evaluating…" : "Run evaluation"}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="challenge-loading">
              {loadState === "error" ? "Connect the evaluator to load a task." : "Preparing task…"}
            </div>
          )}
        </div>

        {report ? <EvaluationReportView report={report} /> : <EmptyReport />}
      </div>
    </section>
  );
}
