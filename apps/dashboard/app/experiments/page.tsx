"use client";

import { useEffect, useState } from "react";
import { formatStamp } from "../../lib/format";

interface Experiment {
  id: string;
  name: string;
  run_count: number;
  created_at: string | null;
  latest_run: ExperimentRun | null;
}

interface ExperimentRun {
  id: string;
  session_id: string;
  model: string;
  provider: string;
  status: string;
  metrics: {
    final_score?: number;
    iterations_used?: number;
  };
  created_at: string | null;
}

const EVALUATOR_URL = process.env.NEXT_PUBLIC_EVALUATOR_URL ?? "http://localhost:8000";
const MLFLOW_URL = process.env.NEXT_PUBLIC_MLFLOW_URL ?? "http://localhost:5000";

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadExperiments = async () => {
      try {
        const res = await fetch(`${EVALUATOR_URL}/api/experiments`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error(`Evaluator responded ${res.status}`);
        const data = (await res.json()) as Experiment[];
        if (!active) return;
        setExperiments(Array.isArray(data) ? data : []);
        setError(null);
      } catch {
        if (!active) return;
        setError(
          "Experiment records could not be loaded. Start the evaluator service and refresh.",
        );
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadExperiments();
    const interval = window.setInterval(() => void loadExperiments(), 3000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <>
      <section className="page-head" aria-labelledby="experiments-title">
        <div>
          <p className="eyebrow">MLOps tracking</p>
          <h1 id="experiments-title">
            Experiments,
            <br />
            <em>under version.</em>
          </h1>
          <p>
            Every tracked experiment recorded in the evaluator database, linked through to its full
            parameter and metric history in MLflow.
          </p>
        </div>
        <dl className="page-metrics">
          <div>
            <dt>Experiments</dt>
            <dd>{loading ? "—" : experiments.length}</dd>
          </div>
          <div>
            <dt>Tracker</dt>
            <dd>MLflow</dd>
          </div>
        </dl>
      </section>

      <section className="console-shell" aria-label="Experiment registry">
        {error ? (
          <div className="service-error" role="alert">
            <strong>Evaluator notice</strong>
            <span>{error}</span>
          </div>
        ) : null}

        <div className="console-panel">
          <div className="panel-bar">
            <h2>Experiment registry</h2>
            <a className="out-link" href={MLFLOW_URL} target="_blank" rel="noreferrer">
              Open MLflow ↗
            </a>
          </div>

          {loading ? (
            <div className="console-empty">
              <p className="muted">Reading experiment registry…</p>
            </div>
          ) : experiments.length === 0 ? (
            <div className="console-empty">
              <div className="empty-mark" aria-hidden="true">
                →
              </div>
              <strong>No experiments tracked yet.</strong>
              <p>
                Run <code>benchmarks/run_agent.py</code> with MLflow enabled to register an
                experiment, then reload this page.
              </p>
            </div>
          ) : (
            <div className="panel-scroll">
              <table className="data-table">
                <caption className="sr-only">Tracked MLOps experiment runs</caption>
                <thead>
                  <tr>
                    <th scope="col">Experiment</th>
                    <th scope="col">Runs</th>
                    <th scope="col">Latest run</th>
                    <th scope="col">Score</th>
                    <th scope="col">Created</th>
                    <th scope="col">Telemetry</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.map((experiment) => (
                    <tr key={experiment.id}>
                      <td>
                        <strong>{experiment.name}</strong>
                        <div className="mono">{experiment.id}</div>
                      </td>
                      <td>{experiment.run_count}</td>
                      <td>
                        {experiment.latest_run ? (
                          <>
                            <a
                              className="out-link"
                              href={`/sessions/${experiment.latest_run.session_id}`}
                            >
                              {experiment.latest_run.status}
                            </a>
                            <div className="muted">
                              {experiment.latest_run.provider} / {experiment.latest_run.model}
                            </div>
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        {experiment.latest_run?.metrics.final_score ?? "—"}
                        {experiment.latest_run?.metrics.iterations_used
                          ? ` / ${experiment.latest_run.metrics.iterations_used} iter.`
                          : ""}
                      </td>
                      <td className="stamp">{formatStamp(experiment.created_at)}</td>
                      <td>
                        <a
                          className="out-link"
                          href={MLFLOW_URL}
                          target="_blank"
                          rel="noreferrer"
                          aria-label={`View ${experiment.name} in MLflow`}
                        >
                          View in MLflow ↗
                        </a>
                      </td>
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
