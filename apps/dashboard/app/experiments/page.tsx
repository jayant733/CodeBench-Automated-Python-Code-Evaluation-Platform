"use client";

import { useEffect, useState } from "react";
import { formatStamp } from "../../lib/format";

interface Experiment {
  id: string;
  name: string;
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
    fetch(`${EVALUATOR_URL}/api/experiments`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Evaluator responded ${res.status}`);
        return (await res.json()) as Experiment[];
      })
      .then((data) => {
        if (!active) return;
        setExperiments(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError(
          "Experiment records could not be loaded. Start the evaluator service and refresh.",
        );
        setLoading(false);
      });
    return () => {
      active = false;
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
                    <th scope="col">Name</th>
                    <th scope="col">Created</th>
                    <th scope="col">Telemetry</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.map((experiment) => (
                    <tr key={experiment.id}>
                      <td className="mono">{experiment.id}</td>
                      <td>
                        <strong>{experiment.name}</strong>
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
