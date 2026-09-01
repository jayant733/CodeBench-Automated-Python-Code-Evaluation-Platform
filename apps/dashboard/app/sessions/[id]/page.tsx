"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
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

interface ToolCall {
  id: string | null;
  tool_name: string;
  arguments: Record<string, unknown> | null;
  result: unknown;
  duration_ms: number | null;
}

interface Iteration {
  iteration_number: number;
  coding_duration_ms: number | null;
  review_verdict: string | { approved?: boolean } | null;
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
  iterations: Iteration[] | null;
}

const EVALUATOR_URL = process.env.NEXT_PUBLIC_EVALUATOR_URL ?? "http://localhost:8000";

/** The orchestrator persists this verdict as a "PASS"/"FAIL" string, older rows as an object. */
function reviewLabel(verdict: Iteration["review_verdict"]): string | null {
  if (verdict == null) return null;
  if (typeof verdict === "string") return verdict;
  if (typeof verdict.approved === "boolean") return verdict.approved ? "PASS" : "FAIL";
  return null;
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

  useEffect(() => {
    if (!id) return;
    let active = true;
    fetch(`${EVALUATOR_URL}/api/agent/sessions/${encodeURIComponent(id)}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Evaluator responded ${res.status}`);
        return (await res.json()) as SessionDetails;
      })
      .then((data) => {
        if (!active) return;
        setSession(data);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

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
            <dd>{session.iterations_used}</dd>
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
                <strong>{session.iterations_used}</strong>
              </div>
              <div className="stat">
                <span>Total duration</span>
                <strong>{formatDuration(session.total_duration_ms)}</strong>
              </div>
            </dl>
          </div>

          <div className="console-panel">
            <div className="panel-bar">
              <h2>Iteration timeline</h2>
              <span className="muted">
                {iterations.length} {iterations.length === 1 ? "iteration" : "iterations"}
              </span>
            </div>

            {iterations.length === 0 ? (
              <div className="console-empty">
                <strong>No iterations recorded.</strong>
                <p>This session ended before the agent completed a coding pass.</p>
              </div>
            ) : (
              <ol className="timeline">
                {iterations.map((iteration) => {
                  const toolCalls = iteration.tool_calls ?? [];
                  const review = reviewLabel(iteration.review_verdict);
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
                            </div>
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
