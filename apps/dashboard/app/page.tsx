import { EvaluationWorkspace } from "../components/evaluation-workspace";

export default function HomePage() {
  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-kicker" aria-hidden="true">
          <span>Run</span>
          <span>Measure</span>
          <span>Improve</span>
        </div>
        <div>
          <p className="eyebrow">Deterministic code assessment</p>
          <h1 id="hero-title">
            Code evaluation,
            <br />
            <em>with receipts.</em>
          </h1>
        </div>
        <p className="hero-copy">
          Submit Python against visible and hidden cases. Every result explains what ran, what
          failed, and how the score was built—inside a disposable Docker sandbox.
        </p>
      </section>

      <EvaluationWorkspace />
    </>
  );
}
