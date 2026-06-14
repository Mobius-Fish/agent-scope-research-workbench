from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def make_run_dir(base_dir: str | Path = "runs") -> Path:
    """Create a timestamped run directory."""

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(base_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_run_artifacts(result: dict[str, Any], run_dir: Path) -> None:
    """Save full intermediate state and per-agent artifacts for debugging."""

    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "state.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    logs = result.get("logs", [])
    (run_dir / "logs.txt").write_text("\n".join(logs), encoding="utf-8")

    for key in [
        "perspectives",
        "tasks",
        "sources",
        "notes",
        "verified_claims",
        "verification_issues",
    ]:
        (run_dir / f"{key}.json").write_text(
            json.dumps(result.get(key, []), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    supervisor_snapshot = {
        "research_round": result.get("research_round"),
        "max_research_rounds": result.get("max_research_rounds"),
        "supervisor_decision": result.get("supervisor_decision"),
        "supervisor_reason": result.get("supervisor_reason"),
        "needs_more_research": result.get("needs_more_research"),
    }
    (run_dir / "supervisor.json").write_text(
        json.dumps(supervisor_snapshot, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    draft_report = result.get("draft_report", "")
    (run_dir / "draft_report.md").write_text(draft_report, encoding="utf-8")

    critique = result.get("critique", "")
    (run_dir / "critique.md").write_text(critique, encoding="utf-8")

    final_report = result.get("final_report", "")
    (run_dir / "report.md").write_text(final_report, encoding="utf-8")
