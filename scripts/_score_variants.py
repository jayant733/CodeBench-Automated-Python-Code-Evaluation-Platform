"""Score the reference and known-bad solutions so the UI's expected output is verifiable."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

API = "http://localhost:8000"
TASK = "palindrome-normalization"
ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "python" / TASK

VARIANTS = {
    "reference_solution": ROOT / "reference_solution.py",
    "raw-comparison (bad)": ROOT / "incorrect_solutions" / "raw-comparison.py",
    "reject-empty (bad)": ROOT / "incorrect_solutions" / "reject-empty-normalization.py",
}


def score(source: str) -> dict:
    payload = json.dumps({"task_id": TASK, "source_code": source}).encode()
    req = urllib.request.Request(
        f"{API}/api/evaluations",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    for label, path in VARIANTS.items():
        report = score(path.read_text(encoding="utf-8"))
        failures = [t["id"] for t in report["visible_tests"] if t["status"] != "passed"]
        print(
            f"{label:24} score={report['score']:3} passed={report['passed']!s:5} "
            f"hidden={report['hidden_test_summary']} visible_failures={failures}"
        )
        print(f"{'':24} breakdown={report['score_breakdown']}")


if __name__ == "__main__":
    main()
