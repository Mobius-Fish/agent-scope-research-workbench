from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from agent_scope.graph import build_graph
from agent_scope.run_artifacts import save_run_artifacts
from agent_scope.evals.rubric import score_result

app = typer.Typer(help="Run deterministic benchmark evaluations for AgentScope Research Workbench.")
console = Console()


DEFAULT_BENCHMARK_PATH = Path("evals/benchmarks/agent_research_v1.jsonl")
DEFAULT_RESULTS_DIR = Path("evals/results")


def _load_benchmark(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
        if "id" not in item or "question" not in item:
            raise ValueError(f"Benchmark row must include id and question at {path}:{line_no}")
        rows.append(item)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _flatten_for_csv(row: dict[str, Any]) -> dict[str, Any]:
    scores = row.get("scores", {})
    return {
        "id": row.get("id"),
        "category": row.get("category"),
        "question": row.get("question"),
        "overall_score": scores.get("overall_score"),
        "grade": scores.get("grade"),
        "source_count": scores.get("source_count"),
        "claim_count": scores.get("claim_count"),
        "supported_claim_ratio": scores.get("supported_claim_ratio"),
        "claims_with_sources_ratio": scores.get("claims_with_sources_ratio"),
        "verification_issue_count": scores.get("verification_issue_count"),
        "unsupported_claim_count": scores.get("unsupported_claim_count"),
        "section_coverage": scores.get("section_coverage"),
        "source_citation_count_in_report": scores.get("source_citation_count_in_report"),
        "final_report_length": scores.get("final_report_length"),
        "has_revision_loop": scores.get("has_revision_loop"),
        "researcher_iterations": scores.get("researcher_iterations"),
        "run_dir": row.get("run_dir"),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    flat_rows = [_flatten_for_csv(row) for row in rows]
    if not flat_rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(flat_rows)


def _build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"case_count": 0}

    scores = [row["scores"] for row in rows]
    return {
        "case_count": len(rows),
        "average_overall_score": round(mean(s["overall_score"] for s in scores), 2),
        "average_source_count": round(mean(s["source_count"] for s in scores), 2),
        "average_claim_count": round(mean(s["claim_count"] for s in scores), 2),
        "average_supported_claim_ratio": round(mean(s["supported_claim_ratio"] for s in scores), 4),
        "average_claims_with_sources_ratio": round(mean(s["claims_with_sources_ratio"] for s in scores), 4),
        "average_section_coverage": round(mean(s["section_coverage"] for s in scores), 4),
        "success_count": sum(1 for s in scores if s["has_final_report"]),
        "revision_loop_success_count": sum(1 for s in scores if s["has_revision_loop"]),
        "grade_distribution": {
            grade: sum(1 for s in scores if s["grade"] == grade)
            for grade in ["A", "B", "C", "D", "F"]
        },
    }


def _write_markdown_report(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# AgentScope Evaluation Report",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- **{key}**: {value}")

    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| ID | Category | Score | Grade | Sources | Claims | Supported Ratio | Issues | Report Length |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        s = row["scores"]
        lines.append(
            "| {id} | {category} | {overall_score} | {grade} | {source_count} | {claim_count} | {supported_claim_ratio} | {verification_issue_count} | {final_report_length} |".format(
                id=row.get("id"),
                category=row.get("category", ""),
                overall_score=s.get("overall_score"),
                grade=s.get("grade"),
                source_count=s.get("source_count"),
                claim_count=s.get("claim_count"),
                supported_claim_ratio=s.get("supported_claim_ratio"),
                verification_issue_count=s.get("verification_issue_count"),
                final_report_length=s.get("final_report_length"),
            )
        )

    lines.extend(
        [
            "",
            "## How to Interpret These Scores",
            "",
            "These are deterministic workflow-quality metrics. They do not prove factual correctness by themselves.",
            "Use them for regression testing, comparing workflow versions, and detecting broken agent stages.",
            "For deeper quality assessment, manually inspect the generated reports and add LLM-as-judge or human scoring later.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _render_table(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    table = Table(title="AgentScope Evaluation Results")
    table.add_column("ID")
    table.add_column("Category")
    table.add_column("Score", justify="right")
    table.add_column("Grade", justify="center")
    table.add_column("Sources", justify="right")
    table.add_column("Claims", justify="right")
    table.add_column("Supported", justify="right")
    table.add_column("Issues", justify="right")

    for row in rows:
        s = row["scores"]
        table.add_row(
            str(row.get("id")),
            str(row.get("category", "")),
            str(s.get("overall_score")),
            str(s.get("grade")),
            str(s.get("source_count")),
            str(s.get("claim_count")),
            str(s.get("supported_claim_ratio")),
            str(s.get("verification_issue_count")),
        )
    console.print(table)
    console.print(f"Average score: [bold]{summary.get('average_overall_score')}[/bold]")


@app.command()
def run(
    benchmark: Path = typer.Option(
        DEFAULT_BENCHMARK_PATH,
        "--benchmark",
        "-b",
        help="Path to JSONL benchmark file.",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_RESULTS_DIR,
        "--output-dir",
        "-o",
        help="Directory where evaluation results should be written.",
    ),
    max_research_rounds: int = typer.Option(
        1,
        "--max-research-rounds",
        min=1,
        max=5,
        help="Maximum researcher/verifier iterations per benchmark case.",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        help="Only run the first N benchmark cases.",
    ),
    save_case_artifacts: bool = typer.Option(
        True,
        "--save-case-artifacts/--no-save-case-artifacts",
        help="Save full per-case LangGraph state and reports under the eval result directory.",
    ),
) -> None:
    """Run the benchmark and write JSONL/CSV/Markdown results."""

    cases = _load_benchmark(benchmark)
    if limit is not None:
        cases = cases[:limit]
    if not cases:
        raise typer.BadParameter("No benchmark cases found.")

    eval_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_root = output_dir / eval_id
    run_root.mkdir(parents=True, exist_ok=True)

    graph = build_graph()
    rows: list[dict[str, Any]] = []

    for index, case in enumerate(cases, start=1):
        console.print(f"\n[bold]Running case {index}/{len(cases)}:[/bold] {case['id']} — {case['question']}")
        result = graph.invoke(
            {
                "user_question": case["question"],
                "logs": [],
                "research_round": 1,
                "max_research_rounds": max_research_rounds,
            }
        )
        scores = score_result(result)
        case_dir = run_root / "cases" / str(case["id"])
        if save_case_artifacts:
            save_run_artifacts(result, case_dir)

        rows.append(
            {
                "id": case["id"],
                "category": case.get("category", ""),
                "question": case["question"],
                "expected_focus": case.get("expected_focus", []),
                "scores": scores,
                "run_dir": str(case_dir) if save_case_artifacts else None,
            }
        )
        console.print(f"Score={scores['overall_score']} Grade={scores['grade']}")

    summary = _build_summary(rows)

    _write_jsonl(run_root / "results.jsonl", rows)
    _write_csv(run_root / "results.csv", rows)
    (run_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_markdown_report(run_root / "report.md", rows, summary)

    _render_table(rows, summary)
    console.print(f"\nSaved evaluation results to: [bold]{run_root}[/bold]")


if __name__ == "__main__":
    app()
