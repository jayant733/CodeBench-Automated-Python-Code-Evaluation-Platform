"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { StatusPill } from "../../../components/status-pill";
import { formatDuration } from "../../../lib/format";

interface SecurityFinding {
  category: string;
  severity: string;
  evidence: string;
  recommendation: string;
}

interface SecurityVerdict {
  safe: boolean;
  risk_level: string;
  findings: SecurityFinding[] | null;
}

interface ReviewIssue {
  severity: string;
  location: string;
  description: string;
  fix_hint: string | null;
}

interface ReviewVerdict {
  approved?: boolean;
  quality_score?: number;
  issues?: ReviewIssue[] | null;
  suggestions?: string[] | null;
}

interface ToolCall {
  id: string | null;
  tool_name: string;
  arguments: Record<string, unknown> | null;
  result: unknown;
  error: string | null;
  duration_ms: number | null;
}

interface Iteration {
  iteration_number: number;
  coding_duration_ms: number | null;
  evaluation_id: string | null;
  review_verdict: string | ReviewVerdict | null;
  security_verdict: SecurityVerdict | null;
  tool_calls: ToolCall[] | null;
}

interface SessionDetails {
  id: string;
  task_id: string;
  status: string;
  final_score: number | null;
  iterations_used: number;
  total_duration_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  iterations: Iteration[] | null;
}

const EVALUATOR_URL = process.env.NEXT_PUBLIC_EVALUATOR_URL ?? "http://localhost:8000";
const POLL_INTERVAL_MS = 2000;

/** The orchestrator persists the reviewer verdict as an object, older rows as a string. */
function reviewLabel(verdict: Iteration["review_verdict"]): string | null {
  if (verdict == null) return null;
  if (typeof verdict === "string") return verdict;
  if (typeof verdict.approved === "boolean") return verdict.approved ? "PASS" : "FAIL";
  return null;
}

function reviewDetail(verdict: Iteration["review_verdict"]): ReviewVerdict | null {
  return verdict != null && typeof verdict === "object" ? verdict : null;
}

function ShellMessage({ children }: { children: React.ReactNode }) {
  return (
    <>
      <section className="page-head">
        <div>
          <Link className="back-link" href="/sessions">
            ← All sessions
          </Link>
          <p className="eyebrow">Run trace</p>
          <h1>
            Session <em>trace.</em>
          </h1>
        </div>
      </section>
      <section className="console-shell">
        <div className="console-panel">
          <div className="console-empty">{children}</div>
        </div>
      </section>
    </>
  );
}

export default function SessionDetailsPage() {
  const params = useParams<{ id: string }>();
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [session, setSession] = useState<SessionDetails | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    async (signal: AbortSignal) => {
      const res = await fetch(
        `${EVALUATOR_URL}/api/agent/sessions/${encodeURIComponent(id ?? "")}`,
        {
          signal,
          cache: "no-store",
        },
      );
      if (!res.ok) throw new Error(`Evaluator responded ${res.status}`);
      return (await res.json()) as SessionDetails;
    },
    [id],
  );

  useEffect(() => {
    if (!id) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let active = true;

    async function poll() {
      let current: SessionDetails | null = null;
      try {
        current = await load(controller.signal);
        if (!active) return;
        setSession(current);
      } catch (caught) {
        if (!active || (caught as Error).name === "AbortError") return;
      } finally {
        if (active) {
          setLoading(false);
          // Keep polling while the orchestrator is still working on this session.
          if (current == null || current.status === "in_progress") {
            timer = setTimeout(poll, POLL_INTERVAL_MS);
          }
        }
      }
    }

    void poll();
    return () => {
      active = false;
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [id, load]);

  if (loading) {
    return (
      <ShellMessage>
        <p className="muted">Reading iteration trace…</p>
      </ShellMessage>
    );
  }

  if (!session) {
    return (
      <ShellMessage>
        <div className="empty-mark" aria-hidden="true">
          →
        </div>
        <strong>Session unavailable.</strong>
        <p>
          This run could not be found, or the evaluator service is not reachable. Return to the run
          history and pick another session.
        </p>
      </ShellMessage>
    );
  }

  const iterations = session.iterations ?? [];
  const totalTokens = (session.prompt_tokens ?? 0) + (session.completion_tokens ?? 0);

  return (
    <>
      <section className="page-head" aria-labelledby="session-title">
        <div>
          <Link className="back-link" href="/sessions">
            ← All sessions
          </Link>
          <p className="eyebrow">Run trace</p>
          <h1 id="session-title">{session.task_id}</h1>
          <p className="detail-id">Session {session.id}</p>
        </div>
        <dl className="page-metrics">
          <div>
            <dt>Score</dt>
            <dd>{session.final_score == null ? "—" : `${session.final_score} / 100`}</dd>
          </div>
          <div>
            <dt>Iterations</dt>
            <dd>{iterations.length || session.iterations_used}</dd>
          </div>
          <div>
            <dt>Duration</dt>
            <dd>{formatDuration(session.total_duration_ms)}</dd>
          </div>
        </dl>
      </section>

      <section className="console-shell" aria-label="Session detail">
        <div className="console-stack">
          <div className="console-panel">
            <div className="panel-bar">
              <h2>Run overview</h2>
              <StatusPill status={session.status} />
            </div>
            <dl className="stat-grid">
              <div className="stat">
                <span>Task</span>
                <strong className="mono">{session.task_id}</strong>
              </div>
              <div className="stat">
                <span>Final score</span>
                <strong>
                  {session.final_score == null ? "—" : session.final_score}
                  <span className="unit"> / 100</span>
                </strong>
              </div>
              <div className="stat">
                <span>Iterations used</span>
                <strong>{iterations.length || session.iterations_used}</strong>
              </div>
              <div className="stat">
                <span>Total duration</span>
                <strong>{formatDuration(session.total_duration_ms)}</strong>
              </div>
              <div className="stat">
                <span>Tokens</span>
                <strong>{totalTokens ? totalTokens.toLocaleString() : "—"}</strong>
              </div>
            </dl>
          </div>

          <div className="console-panel">
            <div className="panel-bar">
              <h2>Iteration timeline</h2>
              <span className="muted">
                {session.status === "in_progress"
                  ? `${iterations.length} so far · running`
                  : `${iterations.length} ${iterations.length === 1 ? "iteration" : "iterations"}`}
              </span>
            </div>

            {iterations.length === 0 ? (
              <div className="console-empty">
                <strong>
                  {session.status === "in_progress"
                    ? "Waiting for the first iteration…"
                    : "No iterations recorded."}
                </strong>
                <p>
                  {session.status === "in_progress"
                    ? "This view refreshes automatically as the orchestrator reports progress."
                    : "This session ended before the agent completed a coding pass."}
                </p>
              </div>
            ) : (
              <ol className="timeline">
                {iterations.map((iteration) => {
                  const toolCalls = iteration.tool_calls ?? [];
                  const review = reviewLabel(iteration.review_verdict);
                  const reviewInfo = reviewDetail(iteration.review_verdict);
                  const security = iteration.security_verdict;

                  return (
                    <li key={iteration.iteration_number}>
                      <span className="iteration-marker" aria-hidden="true">
                        {String(iteration.iteration_number).padStart(2, "0")}
                      </span>
                      <article className="iteration-card">
                        <div className="iteration-card__bar">
                          <h3>Iteration {iteration.iteration_number}</h3>
                          <span>{formatDuration(iteration.coding_duration_ms)}</span>
                        </div>
                        <div className="iteration-card__body">
                          <p className="field-label">Tool calls · {toolCalls.length}</p>
                          {toolCalls.length === 0 ? (
                            <p className="no-tools">No tools were called in this iteration.</p>
                          ) : (
                            <ul className="tool-call-list">
                              {toolCalls.map((call) => (
                                <li
                                  className="tool-call"
                                  key={
                                    call.id ??
                                    `${call.tool_name}:${JSON.stringify(call.arguments ?? {})}`
                                  }
                                >
                                  <b>{call.tool_name}</b>
                                  <code>{JSON.stringify(call.arguments ?? {})}</code>
                                  {call.error ? (
                                    <span className="verdict-row__risk">{call.error}</span>
                                  ) : null}
                                  {call.duration_ms == null ? null : (
                                    <span>{formatDuration(call.duration_ms)}</span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          )}

                          {review ? (
                            <div
                              className={`verdict-row verdict-row--${review === "PASS" ? "safe" : "risk"}`}
                            >
                              <h4>Code review</h4>
                              <span className={`pill pill--${review === "PASS" ? "ok" : "fail"}`}>
                                <i aria-hidden="true" />
                                {review}
                              </span>
                              {reviewInfo?.quality_score == null ? null : (
                                <span className="verdict-row__risk">
                                  quality {reviewInfo.quality_score}/10
                                </span>
                              )}
                            </div>
                          ) : null}

                          {reviewInfo?.issues?.length ? (
                            <ul className="findings-list">
                              {reviewInfo.issues.map((issue) => (
                                <li
                                  key={`${issue.severity}:${issue.location}:${issue.description}`}
                                >
                                  <b>
                                    {issue.severity} · {issue.location}
                                  </b>
                                  <p>{issue.description}</p>
                                </li>
                              ))}
                            </ul>
                          ) : null}

                          {security ? (
                            <div
                              className={`verdict-row verdict-row--${security.safe ? "safe" : "risk"}`}
                            >
                              <h4>Security review</h4>
                              <span className={`pill pill--${security.safe ? "ok" : "fail"}`}>
                                <i aria-hidden="true" />
                                {security.safe ? "Pass" : "Fail"}
                              </span>
                              {security.safe ? null : (
                                <span className="verdict-row__risk">
                                  {security.risk_level} risk
                                </span>
                              )}
                            </div>
                          ) : null}

                          {security?.findings?.length ? (
                            <ul className="findings-list">
                              {security.findings.map((finding) => (
                                <li
                                  key={`${finding.category}:${finding.severity}:${finding.evidence}`}
                                >
                                  <b>
                                    {finding.severity} · {finding.category.replace(/_/g, " ")}
                                  </b>
                                  <p>{finding.evidence}</p>
                                </li>
                              ))}
                            </ul>
                          ) : null}
                        </div>
                      </article>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
