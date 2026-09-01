"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatusPill } from "../../components/status-pill";
import { formatDuration, formatStamp, shortId } from "../../lib/format";

interface AgentSession {
  id: string;
  task_id: string;
  status: string;
  final_score: number | null;
  iterations_used: number;
  total_duration_ms: number;
  created_at: string | null;
}

const EVALUATOR_URL = process.env.NEXT_PUBLIC_EVALUATOR_URL ?? "http://localhost:8000";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${EVALUATOR_URL}/api/agent/sessions`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Evaluator responded ${res.status}`);
        return (await res.json()) as AgentSession[];
      })
      .then((data) => {
        if (!active) return;
        setSessions(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError("Agent history could not be loaded. Start the evaluator service and refresh.");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const scored = sessions.filter((session) => session.final_score != null);
  const averageScore = scored.length
    ? Math.round(scored.reduce((total, s) => total + (s.final_score ?? 0), 0) / scored.length)
    : null;
  const completed = sessions.filter((session) => session.status === "completed").length;

  return (
    <>
      <section className="page-head" aria-labelledby="sessions-title">
        <div>
          <p className="eyebrow">Agent telemetry</p>
          <h1 id="sessions-title">
            Agent runs,
            <br />
            <em>step by step.</em>
          </h1>
          <p>
            Every autonomous attempt the orchestrator has recorded—scored, timed, and traceable down
            to the individual tool call.
          </p>
        </div>
        <dl className="page-metrics">
          <div>
            <dt>Runs</dt>
            <dd>{loading ? "—" : sessions.length}</dd>
          </div>
          <div>
            <dt>Completed</dt>
            <dd>{loading ? "—" : completed}</dd>
          </div>
          <div>
            <dt>Avg score</dt>
            <dd>{averageScore == null ? "—" : averageScore}</dd>
          </div>
        </dl>
      </section>

      <section className="console-shell" aria-label="Agent run history">
        {error ? (
          <div className="service-error" role="alert">
            <strong>Evaluator notice</strong>
            <span>{error}</span>
          </div>
        ) : null}

        <div className="console-panel">
          <div className="panel-bar">
            <h2>Execution log</h2>
            <span className="muted">{loading ? "Loading…" : `${sessions.length} sessions`}</span>
          </div>

          {loading ? (
            <div className="console-empty">
              <p className="muted">Reading agent history…</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="console-empty">
              <div className="empty-mark" aria-hidden="true">
                →
              </div>
              <strong>No agent sessions yet.</strong>
              <p>
                Run <code>benchmarks/run_agent.py</code> to record an autonomous attempt, then
                reload this page.
              </p>
            </div>
          ) : (
            <div className="panel-scroll">
              <table className="data-table">
                <caption className="sr-only">Historical agent execution sessions</caption>
                <thead>
                  <tr>
                    <th scope="col">Session</th>
                    <th scope="col">Task</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="num">
                      Score
                    </th>
                    <th scope="col" className="num">
                      Iterations
                    </th>
                    <th scope="col" className="num">
                      Duration
                    </th>
                    <th scope="col">Started</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((session) => (
                    <tr key={session.id}>
                      <td>
                        <Link className="id-link" href={`/sessions/${session.id}`}>
                          {shortId(session.id)}
                        </Link>
                      </td>
                      <td className="mono">{session.task_id}</td>
                      <td>
                        <StatusPill status={session.status} />
                      </td>
                      <td className="num">
                        {session.final_score == null ? (
                          "—"
                        ) : (
                          <span className="score-cell">
                            <strong>{session.final_score}</strong>
                            <span
                              className={`score-meter${session.final_score < 50 ? " score-meter--low" : ""}`}
                              aria-hidden="true"
                            >
                              <i style={{ width: `${Math.min(session.final_score, 100)}%` }} />
                            </span>
                          </span>
                        )}
                      </td>
                      <td className="num">{session.iterations_used}</td>
                      <td className="num">{formatDuration(session.total_duration_ms)}</td>
                      <td className="stamp">{formatStamp(session.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
