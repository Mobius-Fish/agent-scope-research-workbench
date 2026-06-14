# AgentScope Research Workbench

AgentScope Research Workbench is a LangGraph-based multi-agent deep research system. It decomposes complex research questions into multiple expert perspectives, dispatches research tasks, collects web evidence, converts findings into source-grounded claims, verifies those claims, controls research loops with a supervisor, critiques draft reports, revises them into final reports, and evaluates the workflow with repeatable benchmark cases.

The project is designed as an advanced learning and portfolio project for building practical agentic systems. It is not just a chatbot or a simple RAG demo; it is a structured, observable, and evaluable multi-agent research workflow.

---

## 1. Key Features

- **LangGraph workflow orchestration**: stateful graph execution with explicit nodes, edges, and conditional routing.
- **STORM-style perspective generation**: generates multiple expert perspectives before planning research tasks.
- **Planner Agent**: converts the user question and generated perspectives into concrete research tasks.
- **Researcher Agent**: calls web search tools, collects sources, and produces structured research notes.
- **Claim/Source data model**: converts research outputs into atomic claims linked to source ids.
- **Verifier Agent**: checks whether claims have valid source grounding and marks them as `supported`, `weak`, or `unsupported`.
- **Supervisor control loop**: decides whether to run another research round or proceed to writing.
- **Writer → Critic → Reviser loop**: drafts a report, critiques it, and revises it into a final report.
- **Streamlit dashboard**: visualizes perspectives, tasks, sources, claims, verification issues, reports, and raw state.
- **Evaluation benchmark**: runs repeatable benchmark questions and reports deterministic workflow-quality metrics.
- **Run artifacts**: saves every run into a timestamped directory for debugging and analysis.

---

## 2. System Workflow

The current workflow is:

```text
START
  ↓
perspective
  ↓
planner
  ↓
researcher
  ↓
verifier
  ↓
supervisor
  ├── researcher   # when more research is needed and budget remains
  └── writer       # when evidence is sufficient or max rounds reached
        ↓
      critic
        ↓
      reviser
        ↓
       END
```

Conceptually:

```text
Question
  → Perspectives
  → Research Tasks
  → Sources + Claims
  → Verification
  → Supervisor Routing
  → Draft Report
  → Critique
  → Final Report
  → Evaluation
```

---

## 3. Agent Responsibilities

### Perspective Agent

Generates diverse expert perspectives for the research question, such as technical, product, market, safety, open-source, and evaluation perspectives.

Purpose:

- Broaden the research scope.
- Reduce one-sided planning.
- Prepare the system for specialist-agent routing later.

### Planner Agent

Converts the user question and generated perspectives into a small set of concrete research tasks.

Outputs:

- `research_goal`
- `tasks`
- each task includes `id`, `question`, `perspective`, `priority`, and `search_queries`

### Researcher Agent

Runs web searches for each task and summarizes the retrieved evidence into structured research notes.

Outputs:

- `sources`
- `notes`
- `claims`
- `limitations`

### Verifier Agent

Checks whether each claim is source-grounded.

Current deterministic checks include:

- claim text is non-empty
- claim has `source_ids`
- referenced source ids exist
- source URL is valid
- source content is non-empty
- confidence is not too low

Outputs:

- `verified_claims`
- `verification_issues`
- `needs_more_research`

### Supervisor Agent

Uses the verifier's quality signal to decide whether to loop back to the Researcher Agent or proceed to writing.

Routing logic:

```text
if needs_more_research and research_round < max_research_rounds:
    route to researcher
else:
    route to writer
```

### Writer Agent

Generates a draft report from the verified claims, notes, sources, and verification issues.

Output:

- `draft_report`

### Critic Agent

Reviews the draft report and identifies issues such as unsupported claims, overconfident wording, missing perspectives, weak citations, and unclear recommendations.

Output:

- `critique`

### Reviser Agent

Uses the draft report and critique to produce the final Markdown report.

Output:

- `final_report`

---

## 4. Project Structure

```text
agent-scope-research-workbench/
├── .env.example
├── .gitignore
├── README.md
├── pyproject.toml
├── examples/
│   └── questions.md
├── reports/
│   └── .gitkeep
├── evals/
│   ├── benchmarks/
│   │   └── agent_research_v1.jsonl
│   └── results/
└── src/
    └── agent_scope/
        ├── __init__.py
        ├── cli.py
        ├── config.py
        ├── dashboard.py
        ├── graph.py
        ├── llm.py
        ├── models.py
        ├── prompts.py
        ├── run_artifacts.py
        ├── state.py
        ├── agents/
        │   ├── __init__.py
        │   ├── perspective.py
        │   ├── planner.py
        │   ├── researcher.py
        │   ├── verifier.py
        │   ├── supervisor.py
        │   ├── writer.py
        │   ├── critic.py
        │   └── reviser.py
        ├── tools/
        │   ├── __init__.py
        │   └── search.py
        ├── utils/
        │   └── json_utils.py
        └── evals/
            ├── __init__.py
            ├── rubric.py
            └── run_eval.py
```

---

## 5. Core Data Model

The system is built around structured state rather than free-form text passing.

### Source

A source is a piece of evidence retrieved by the Researcher Agent.

Typical fields:

```text
id
title
url
content
score
source_type
search_query
task_id
publisher
published_date
accessed_at
credibility_score
```

### Claim

A claim is an atomic, source-grounded statement produced from research notes.

Typical fields:

```text
id
text
task_id
perspective
source_ids
confidence
verification_status
verification_reason
```

### ResearchNote

A research note is the Researcher Agent's output for one task.

Typical fields:

```text
task_id
perspective
question
summary
claims
limitations
```

### ResearchState

The graph-level state includes:

```text
user_question
research_goal
perspectives
tasks
sources
notes
verified_claims
verification_issues
needs_more_research
research_round
max_research_rounds
supervisor_decision
supervisor_reason
draft_report
critique
final_report
logs
```

---

## 6. Installation

Python 3.11+ is recommended.

```bash
git clone <your-repo-url>
cd agent-scope-research-workbench
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

---

## 7. Environment Variables

Copy the example file:

```bash
cp .env.example .env
```

### DeepSeek Example

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=your_deepseek_api_key
LLM_MODEL_ID=deepseek-chat
TAVILY_API_KEY=your_tavily_api_key
```

### OpenAI Example

```env
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_api_key
LLM_MODEL_ID=gpt-4.1-mini
TAVILY_API_KEY=your_tavily_api_key
```

### OpenAI-Compatible Gateway Example

Use this mode if you are calling a custom gateway, proxy, or another OpenAI-compatible model endpoint.

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_gateway_api_key
LLM_MODEL_ID=your_model_name
LLM_BASE_URL=your_gateway_base_url
TAVILY_API_KEY=your_tavily_api_key
```

---

## 8. Run from CLI

Run a research task:

```bash
agentscope-research run "Compare LangGraph, CrewAI, and AutoGen for building a multi-agent research assistant."
```

Specify the output report path:

```bash
agentscope-research run "What are the major technical challenges in productionizing multi-agent systems?" \
  --output reports/productionizing-agents.md
```

Limit the number of researcher/verifier iterations:

```bash
agentscope-research run "How should a solo developer build a useful AI agent project?" \
  --max-research-rounds 1
```

Allow up to three research rounds:

```bash
agentscope-research run "Evaluate the design of claim-level verification in multi-agent research systems." \
  --max-research-rounds 3
```

Disable trace saving:

```bash
agentscope-research run "Analyze agent evaluation methods." --no-save-trace
```

Depending on your local Typer/script configuration, a single-command shortcut may also work:

```bash
agentscope-research "Compare LangGraph, CrewAI, and AutoGen."
```

If unsure, use the explicit `run` subcommand.

---

## 9. Run the Dashboard

Start the local Streamlit dashboard:

```bash
streamlit run src/agent_scope/dashboard.py
```

The dashboard lets you inspect:

- run logs
- generated perspectives
- planned research tasks
- retrieved sources
- research notes
- verified claims
- verification issues
- supervisor decisions
- draft report
- critique
- final report
- raw final LangGraph state
- latest evaluation benchmark results

Recommended first test:

```text
Max research rounds = 1
Save run artifacts to runs/ = enabled
```

After the structure looks correct, increase `Max research rounds` to 2 or 3.

---

## 10. Run Artifacts

Each CLI or dashboard run can save a full trace under:

```text
runs/<timestamp>/
```

Typical contents:

```text
runs/<timestamp>/
├── state.json
├── logs.txt
├── perspectives.json
├── tasks.json
├── sources.json
├── notes.json
├── verified_claims.json
├── verification_issues.json
├── supervisor.json
├── draft_report.md
├── critique.md
└── report.md
```

Use these files to debug the workflow.

Recommended checks:

- `logs.txt`: confirms which agents ran.
- `perspectives.json`: checks whether research lenses are diverse.
- `tasks.json`: checks whether Planner used the generated perspectives.
- `sources.json`: checks whether web search returned useful sources.
- `notes.json`: checks whether Researcher produced claims and limitations.
- `verified_claims.json`: checks claim-level verification results.
- `verification_issues.json`: checks unsupported or weak evidence.
- `supervisor.json`: checks why the workflow continued or stopped.
- `draft_report.md`, `critique.md`, `report.md`: compares draft, critique, and final revision.

---

## 11. Evaluation Benchmark

The project includes a deterministic benchmark harness for regression testing.

Run one benchmark case:

```bash
agentscope-eval run --limit 1 --max-research-rounds 1
```

Run the full benchmark:

```bash
agentscope-eval run --max-research-rounds 1
```

Run with more research budget:

```bash
agentscope-eval run --max-research-rounds 2
```

Benchmark cases are stored in:

```text
evals/benchmarks/agent_research_v1.jsonl
```

Results are written to:

```text
evals/results/<timestamp>/
```

Typical evaluation output:

```text
evals/results/<timestamp>/
├── summary.json
├── results.jsonl
├── results.csv
├── report.md
└── cases/
    └── <case_id>/
        ├── state.json
        ├── logs.txt
        ├── perspectives.json
        ├── tasks.json
        ├── sources.json
        ├── notes.json
        ├── verified_claims.json
        ├── verification_issues.json
        ├── supervisor.json
        ├── draft_report.md
        ├── critique.md
        └── report.md
```

---

## 12. Evaluation Metrics

The current benchmark uses deterministic metrics. It does not directly prove factual correctness, but it checks whether the workflow produces the expected observable artifacts.

Key metrics include:

```text
perspective_count
task_count
source_count
claim_count
supported_claim_count
weak_claim_count
unsupported_claim_count
claims_with_sources_ratio
supported_claim_ratio
verification_issue_count
section_coverage
source_citation_count_in_report
final_report_length
has_revision_loop
researcher_iterations
supervisor_researcher_routes
overall_score
grade
```

Interpretation:

- A high `claims_with_sources_ratio` means the Researcher is linking claims to evidence.
- A high `supported_claim_ratio` means the Verifier accepted more claims as source-grounded.
- A high `section_coverage` means the final report follows the expected structure.
- `has_revision_loop = true` means Writer, Critic, and Reviser all executed.
- `researcher_iterations > 1` means the Supervisor loop triggered additional research.

Suggested baseline targets:

```text
average_overall_score >= 65
average_claims_with_sources_ratio >= 0.70
revision_loop_success_count == case_count
source_count > 0
claim_count > 0
```

---

## 13. How to Validate Agent Capability

Use four levels of validation.

### Level 1: Smoke Test

```bash
agentscope-eval run --limit 1 --max-research-rounds 1
```

Check:

```text
has_final_report = true
has_revision_loop = true
perspective_count >= 4
task_count >= 3
source_count > 0
claim_count > 0
```

### Level 2: Regression Test

Run the full benchmark after each major code or prompt change:

```bash
agentscope-eval run --max-research-rounds 1
```

Compare:

```text
average_overall_score
average_supported_claim_ratio
average_claims_with_sources_ratio
average_section_coverage
revision_loop_success_count
```

### Level 3: A/B Test

Run the same benchmark before and after changing a prompt, agent, or routing rule. Compare the two `summary.json` files.

Useful questions:

- Did `overall_score` improve?
- Did `supported_claim_ratio` improve?
- Did `source_count` collapse unexpectedly?
- Did `claim_count` become too low or too high?
- Did the final report become longer without better evidence?

### Level 4: Human Review

For selected cases, manually inspect:

```text
evals/results/<timestamp>/cases/<case_id>/report.md
evals/results/<timestamp>/cases/<case_id>/verified_claims.json
evals/results/<timestamp>/cases/<case_id>/sources.json
```

Human review should check:

- Are the main conclusions actually supported by sources?
- Are weak claims labeled as uncertain?
- Are recommendations specific and actionable?
- Did the Critic improve the final report?
- Are important perspectives missing?
- Are there obvious hallucinations or unsupported claims?

---

## 14. Development Workflow

Recommended development loop:

```bash
# 1. Run one quick case
agentscope-eval run --limit 1 --max-research-rounds 1

# 2. Inspect artifacts
ls evals/results/<timestamp>/cases/<case_id>/

# 3. Run from dashboard for visual debugging
streamlit run src/agent_scope/dashboard.py

# 4. Run full benchmark before committing changes
agentscope-eval run --max-research-rounds 1
```

When changing prompts or agents, inspect both metrics and artifacts. Do not optimize only for report length or natural-language fluency.

---

## 15. Troubleshooting

### `ModuleNotFoundError: No module named 'agent_scope'`

Install the project in editable mode from the project root:

```bash
pip install -e .
```

Then run commands from the project root.

### Streamlit cannot import `agent_scope`

Use:

```bash
streamlit run src/agent_scope/dashboard.py
```

If import errors continue, reinstall:

```bash
pip install -e .
```

### No sources are returned

Check:

```text
TAVILY_API_KEY is set
.env is in the project root
search queries in tasks.json are reasonable
network access is available
```

### Claims are mostly unsupported

Inspect:

```text
runs/<timestamp>/notes.json
runs/<timestamp>/verified_claims.json
runs/<timestamp>/sources.json
```

Common causes:

- Researcher produced claims without `source_ids`.
- The model referenced non-existent source ids.
- Search results were empty or low quality.
- The verifier rules are too strict for the current source snippets.

### Dashboard works but benchmark fails

Try a one-case benchmark first:

```bash
agentscope-eval run --limit 1 --max-research-rounds 1
```

Then inspect:

```text
evals/results/<timestamp>/cases/<case_id>/logs.txt
```

---

## 16. Current Limitations

- The Verifier is deterministic and mostly checks structural source-grounding, not deep semantic entailment.
- Web source quality depends heavily on Tavily results and generated search queries.
- The Supervisor currently loops at the whole-researcher level; it does not yet create targeted repair tasks for specific unsupported claims.
- The evaluation benchmark measures workflow quality and artifact completeness, not full factual correctness.
- The dashboard is optimized for local debugging, not production deployment.

---

## 17. Possible Next Improvements

High-impact extensions:

- **LLM-based semantic verifier**: check whether source snippets truly support each claim.
- **Claim-level repair loop**: generate targeted follow-up searches for unsupported claims.
- **Specialized Researcher Agents**: technical, market, academic, open-source, safety, and evaluation researchers.
- **Source credibility scoring**: rank sources by authority, recency, and relevance.
- **Persistent database**: store runs, sources, claims, and reports in SQLite/Postgres.
- **Vector memory**: reuse previous research across runs.
- **FastAPI + Next.js frontend**: replace the Streamlit dashboard with a product-style web app.
- **Human-in-the-loop checkpoints**: let users approve perspectives, tasks, or repair rounds.
- **LLM-as-judge benchmark**: add quality dimensions such as coverage, faithfulness, citation quality, actionability, and risk awareness.

---

## 18. Project Summary

AgentScope Research Workbench is a structured multi-agent research system with:

```text
Perspective generation
Task planning
Web research
Claim extraction
Source tracking
Claim verification
Supervisor-controlled research loops
Draft writing
Critique
Revision
Dashboard observability
Benchmark evaluation
```

It is intended to demonstrate practical agent engineering patterns: stateful orchestration, structured intermediate representations, quality gates, feedback loops, observability, and regression evaluation.
