from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from agent_scope.graph import build_graph
from agent_scope.run_artifacts import make_run_dir, save_run_artifacts


DEFAULT_QUESTION = "Compare LangGraph, CrewAI, and AutoGen for building a multi-agent research assistant."


def _collect_claims(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for note in notes:
        claims.extend(note.get("claims", []) or [])
    return claims


def _status_counts(claims: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"supported": 0, "weak": 0, "unsupported": 0, "unverified": 0}
    for claim in claims:
        status = claim.get("verification_status") or "unverified"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _json_download(label: str, data: Any, file_name: str) -> None:
    st.download_button(
        label=label,
        data=json.dumps(data, ensure_ascii=False, indent=2, default=str),
        file_name=file_name,
        mime="application/json",
    )


def _run_workflow(question: str, max_research_rounds: int) -> dict[str, Any]:
    graph = build_graph()
    return graph.invoke(
        {
            "user_question": question,
            "logs": [],
            "research_round": 1,
            "max_research_rounds": max_research_rounds,
        }
    )


def _render_overview(result: dict[str, Any], run_dir: Path | None) -> None:
    notes = result.get("notes", [])
    verified_claims = result.get("verified_claims", []) or _collect_claims(notes)
    counts = _status_counts(verified_claims)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Perspectives", len(result.get("perspectives", [])))
    col2.metric("Tasks", len(result.get("tasks", [])))
    col3.metric("Sources", len(result.get("sources", [])))
    col4.metric("Claims", len(verified_claims))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Supported", counts.get("supported", 0))
    col6.metric("Weak", counts.get("weak", 0))
    col7.metric("Unsupported", counts.get("unsupported", 0))
    col8.metric("Issues", len(result.get("verification_issues", [])))

    st.subheader("Supervisor decision")
    st.write(
        {
            "decision": result.get("supervisor_decision"),
            "reason": result.get("supervisor_reason"),
            "research_round": result.get("research_round"),
            "max_research_rounds": result.get("max_research_rounds"),
            "needs_more_research": result.get("needs_more_research"),
        }
    )

    if run_dir:
        st.success(f"Run artifacts saved to: {run_dir}")

    st.subheader("Run logs")
    st.code("\n".join(result.get("logs", [])) or "No logs.")



def _render_agent_outputs(result: dict[str, Any]) -> None:
    st.subheader("Perspective Agent output")
    st.dataframe(result.get("perspectives", []), use_container_width=True)
    with st.expander("Raw perspectives JSON"):
        st.json(result.get("perspectives", []))

    st.subheader("Planner Agent output")
    st.dataframe(result.get("tasks", []), use_container_width=True)
    with st.expander("Raw tasks JSON"):
        st.json(result.get("tasks", []))

    st.subheader("Researcher Agent notes")
    notes = result.get("notes", [])
    for note in notes:
        with st.expander(f"{note.get('task_id', '')} · {note.get('perspective', '')} · {note.get('question', '')}"):
            st.markdown("**Summary**")
            st.write(note.get("summary", ""))
            st.markdown("**Claims**")
            st.dataframe(note.get("claims", []), use_container_width=True)
            st.markdown("**Limitations**")
            st.write(note.get("limitations", []))



def _render_claims_and_verification(result: dict[str, Any]) -> None:
    st.subheader("Verified claims")
    verified_claims = result.get("verified_claims", [])
    if verified_claims:
        st.dataframe(verified_claims, use_container_width=True)
    else:
        st.info("No verified claims were produced.")

    st.subheader("Verification issues")
    issues = result.get("verification_issues", [])
    if issues:
        st.dataframe(issues, use_container_width=True)
    else:
        st.success("No deterministic verification issues found.")

    with st.expander("Raw verification JSON"):
        st.json(
            {
                "verified_claims": verified_claims,
                "verification_issues": issues,
                "needs_more_research": result.get("needs_more_research"),
            }
        )



def _render_reports(result: dict[str, Any]) -> None:
    st.subheader("Draft report")
    draft_report = result.get("draft_report", "")
    if draft_report:
        st.markdown(draft_report)
        st.download_button("Download draft_report.md", draft_report, "draft_report.md", "text/markdown")
    else:
        st.info("No draft report available.")

    st.divider()
    st.subheader("Critique")
    critique = result.get("critique", "")
    if critique:
        st.markdown(critique)
        st.download_button("Download critique.md", critique, "critique.md", "text/markdown")
    else:
        st.info("No critique available.")

    st.divider()
    st.subheader("Final report")
    final_report = result.get("final_report", "")
    if final_report:
        st.markdown(final_report)
        st.download_button("Download report.md", final_report, "report.md", "text/markdown")
    else:
        st.info("No final report available.")



def _render_sources(result: dict[str, Any]) -> None:
    st.subheader("Sources")
    sources = result.get("sources", [])
    if sources:
        st.dataframe(sources, use_container_width=True)
    else:
        st.info("No sources were collected.")

    with st.expander("Raw sources JSON"):
        st.json(sources)



def _render_raw_state(result: dict[str, Any]) -> None:
    st.subheader("Raw final LangGraph state")
    st.json(result)
    _json_download("Download state.json", result, "state.json")



def _find_latest_eval_result() -> Path | None:
    results_dir = Path("evals/results")
    if not results_dir.exists():
        return None
    candidates = sorted([p for p in results_dir.iterdir() if p.is_dir()], reverse=True)
    for candidate in candidates:
        if (candidate / "summary.json").exists():
            return candidate
    return None


def _render_latest_evaluation() -> None:
    st.subheader("Latest evaluation benchmark")
    latest = _find_latest_eval_result()
    if latest is None:
        st.info("No evaluation results found yet. Run: agentscope-eval run --limit 1")
        return

    st.write(f"Latest eval directory: `{latest}`")
    summary_path = latest / "summary.json"
    report_path = latest / "report.md"
    csv_path = latest / "results.csv"

    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        st.json(summary)

    if csv_path.exists():
        st.download_button(
            "Download results.csv",
            csv_path.read_text(encoding="utf-8"),
            "results.csv",
            "text/csv",
        )

    if report_path.exists():
        st.markdown(report_path.read_text(encoding="utf-8"))


def main() -> None:
    st.set_page_config(page_title="AgentScope Research Workbench", layout="wide")
    st.title("AgentScope Research Workbench")
    st.caption("Multi-agent deep research workflow: perspective → planner → researcher ↔ verifier/supervisor → writer → critic → reviser")

    with st.sidebar:
        st.header("Run settings")
        max_research_rounds = st.slider("Max research rounds", min_value=1, max_value=5, value=2)
        save_trace = st.checkbox("Save run artifacts to runs/", value=True)
        st.divider()
        st.markdown("**Tip:** 先用 1 轮快速测试，确认输出结构正常后再提高研究轮数。")

    question = st.text_area("Research question", value=DEFAULT_QUESTION, height=140)

    col_run, col_clear = st.columns([1, 1])
    with col_run:
        run_clicked = st.button("Run research", type="primary", use_container_width=True)
    with col_clear:
        clear_clicked = st.button("Clear current result", use_container_width=True)

    if clear_clicked:
        st.session_state.pop("latest_result", None)
        st.session_state.pop("latest_run_dir", None)
        st.rerun()

    if run_clicked:
        if not question.strip():
            st.error("Please enter a research question.")
            return

        with st.spinner("Running agent workflow..."):
            result = _run_workflow(question.strip(), max_research_rounds)
            run_dir: Path | None = None
            if save_trace:
                run_dir = make_run_dir("runs")
                save_run_artifacts(result, run_dir)

        st.session_state["latest_result"] = result
        st.session_state["latest_run_dir"] = str(run_dir) if run_dir else None
        st.success("Research workflow finished.")

    result = st.session_state.get("latest_result")
    if not result:
        st.info("Enter a question and click Run research to inspect each agent's output.")
        return

    run_dir_raw = st.session_state.get("latest_run_dir")
    run_dir = Path(run_dir_raw) if run_dir_raw else None

    tabs = st.tabs(
        [
            "Overview",
            "Agent outputs",
            "Claims & verification",
            "Reports",
            "Sources",
            "Raw state",
            "Evaluation",
        ]
    )

    with tabs[0]:
        _render_overview(result, run_dir)
    with tabs[1]:
        _render_agent_outputs(result)
    with tabs[2]:
        _render_claims_and_verification(result)
    with tabs[3]:
        _render_reports(result)
    with tabs[4]:
        _render_sources(result)
    with tabs[5]:
        _render_raw_state(result)
    with tabs[6]:
        _render_latest_evaluation()


if __name__ == "__main__":
    main()
