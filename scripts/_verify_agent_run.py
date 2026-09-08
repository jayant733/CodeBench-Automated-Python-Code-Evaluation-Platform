"""Launch an agent run through the API and report the persisted iteration trace."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API = "http://localhost:8000"


def request(method: str, url: str, payload: dict | None = None) -> tuple[int, object]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:400]


def main() -> int:
    task_id = sys.argv[1] if len(sys.argv) > 1 else "palindrome-normalization"
    max_iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    code, started = request(
        "POST",
        f"{API}/api/agent/sessions",
        {"task_id": task_id, "max_iterations": max_iterations},
    )
    print(f"POST /api/agent/sessions -> {code} {started}")
    if code != 202 or not isinstance(started, dict):
        return 1

    session_id = started["session_id"]
    detail: dict = {}

    for attempt in range(60):
        time.sleep(3)
        status_code, payload = request("GET", f"{API}/api/agent/sessions/{session_id}")
        if status_code != 200 or not isinstance(payload, dict):
            print(f"  t+{(attempt + 1) * 3}s waiting (HTTP {status_code})")
            continue
        detail = payload
        iterations = detail.get("iterations") or []
        print(
            f"  t+{(attempt + 1) * 3}s status={detail['status']} "
            f"score={detail['final_score']} iterations={len(iterations)} "
            f"tool_calls_per_iteration={[len(i.get('tool_calls') or []) for i in iterations]}"
        )
        if detail["status"] != "in_progress":
            break

    print("\n--- iteration trace ---")
    for iteration in detail.get("iterations") or []:
        review = iteration.get("review_verdict")
        security = iteration.get("security_verdict")
        review_label = (
            review
            if isinstance(review, str)
            else ("PASS" if (review or {}).get("approved") else "FAIL")
            if review
            else "none"
        )
        print(
            f"iteration {iteration['iteration_number']}: "
            f"{iteration['coding_duration_ms']} ms, "
            f"review={review_label}, "
            f"security={'safe' if (security or {}).get('safe') else (security or {}).get('risk_level', 'none')}, "
            f"eval_id={(iteration.get('evaluation_id') or 'none')[:8]}"
        )
        for call in iteration.get("tool_calls") or []:
            args = call.get("arguments") or {}
            preview = {k: (str(v)[:40] + "…" if len(str(v)) > 40 else v) for k, v in args.items()}
            print(f"    tool {call['tool_name']} {preview} {call.get('duration_ms')} ms")

    print("\n--- session summary ---")
    print(
        json.dumps(
            {
                key: detail.get(key)
                for key in (
                    "id",
                    "task_id",
                    "status",
                    "final_score",
                    "iterations_used",
                    "total_duration_ms",
                    "prompt_tokens",
                    "completion_tokens",
                )
            },
            indent=2,
        )
    )

    code, sessions = request("GET", f"{API}/api/agent/sessions")
    print(f"\nGET /api/agent/sessions -> {code}, {len(sessions)} row(s)")
    code, experiments = request("GET", f"{API}/api/experiments")
    print(f"GET /api/experiments -> {code} {experiments}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
