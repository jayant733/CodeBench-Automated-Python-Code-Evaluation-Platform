import { EvaluationWorkspace } from "../components/evaluation-workspace";

export default function HomePage() {
  return (
    <>
      <header className="site-header">
        <a className="brand" href="#workspace" aria-label="AI Code Evaluation Suite home">
          <span className="brand-mark" aria-hidden="true">
            AE
          </span>
          <span>AI Code Evaluation Suite</span>
        </a>
        <div className="header-note">
          <span className="live-dot" aria-hidden="true" />
          Local evaluator
        </div>
      </header>

      <main>
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
      </main>

      <footer>
        <span>Open source · Local first · No fabricated intelligence</span>
        <span>Evaluator MVP / 0.1</span>
      </footer>
    </>
  );
}
