from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from .graph import build_graph
from .run_artifacts import make_run_dir, save_run_artifacts

app = typer.Typer(help="Run AgentScope Research Workbench.")
console = Console()


@app.command()
def run(
    question: str = typer.Argument(..., help="The research question to investigate."),
    output: Optional[Path] = typer.Option(
        Path("reports/report.md"),
        "--output",
        "-o",
        help="Path to save the Markdown report.",
    ),
    save_trace: bool = typer.Option(
        True,
        "--save-trace/--no-save-trace",
        help="Whether to save intermediate run artifacts.",
    ),
    max_research_rounds: int = typer.Option(
        2,
        "--max-research-rounds",
        min=1,
        max=5,
        help="Maximum number of researcher/verifier iterations before writing.",
    ),
):
    """Run perspective -> planner -> researcher/verifier loop -> writer -> critic -> reviser."""

    graph = build_graph()
    result = graph.invoke(
        {
            "user_question": question,
            "logs": [],
            "research_round": 1,
            "max_research_rounds": max_research_rounds,
        }
    )

    logs = result.get("logs", [])
    if logs:
        console.print(Panel("\n".join(logs), title="Run logs", border_style="blue"))

    final_report = result.get("final_report", "")
    console.print(Panel(final_report, title="Final report", border_style="green"))

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(final_report, encoding="utf-8")
        console.print(f"\nSaved report to: [bold]{output}[/bold]")

    if save_trace:
        run_dir = make_run_dir("runs")
        save_run_artifacts(result, run_dir)
        console.print(f"Saved run trace to: [bold]{run_dir}[/bold]")


if __name__ == "__main__":
    app()
