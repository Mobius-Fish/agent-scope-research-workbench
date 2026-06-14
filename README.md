# AgentScope Research Workbench

这是一个最小可运行的 LangGraph 多智能体研究项目骨架，实现了第 2 步和第 3 步：

```text
planner → researcher → writer
```

目标不是一次性做完整系统，而是先跑通一个干净、可扩展的 MVP：

1. `Planner Agent`：把用户问题拆成多个研究任务。
2. `Researcher Agent`：为每个任务调用搜索工具，并生成结构化研究笔记。
3. `Writer Agent`：基于 notes 和 sources 生成 Markdown 研究报告。

后续可以继续加入：`verifier → critic → supervisor → evaluator → frontend dashboard`。

---

## 1. 项目结构

```text
agent-scope-research-workbench/
├── pyproject.toml
├── .env.example
├── README.md
├── examples/
│   └── questions.md
├── reports/
└── src/
    └── agent_scope/
        ├── agents/
        │   ├── planner.py
        │   ├── researcher.py
        │   └── writer.py
        ├── tools/
        │   └── search.py
        ├── utils/
        │   └── json_utils.py
        ├── config.py
        ├── graph.py
        ├── llm.py
        ├── models.py
        ├── prompts.py
        ├── state.py
        └── cli.py
```

---

## 2. 安装

建议使用 Python 3.11+。

```bash
cd agent-scope-research-workbench
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

---

## 3. 配置环境变量

```bash
cp .env.example .env
```

### DeepSeek 示例

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=你的 DeepSeek API Key
LLM_MODEL_ID=deepseek-chat
TAVILY_API_KEY=你的 Tavily API Key
```

### OpenAI 示例

```env
LLM_PROVIDER=openai
LLM_API_KEY=你的 OpenAI API Key
LLM_MODEL_ID=gpt-4.1-mini
TAVILY_API_KEY=你的 Tavily API Key
```

### OpenAI-compatible 网关示例

如果你只有：

```env
LLM_API_KEY=
LLM_MODEL_ID=
LLM_BASE_URL=
```

可以这样配置：

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=你的网关 API Key
LLM_MODEL_ID=你的模型名
LLM_BASE_URL=你的网关 base URL
TAVILY_API_KEY=你的 Tavily API Key
```

---

## 4. 运行

```bash
agentscope-research "Compare LangGraph, CrewAI, and AutoGen for building a multi-agent research assistant."
```

指定输出文件：

```bash
agentscope-research "What are the major technical challenges in productionizing multi-agent systems?" -o reports/productionizing-agents.md
```

也可以用 Python 模块方式运行：

```bash
python -m agent_scope.cli run "Analyze the current ecosystem around AI agent frameworks."
```

---

## 5. 当前 LangGraph 工作流

当前图非常简单：

```text
START
  ↓
planner
  ↓
researcher
  ↓
writer
  ↓
END
```

代码在：

```text
src/agent_scope/graph.py
```

核心代码：

```python
from langgraph.graph import END, START, StateGraph

from .agents.planner import planner_node
from .agents.researcher import researcher_node
from .agents.writer import writer_node
from .state import ResearchState


def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)

    return graph.compile()
```

---

## 6. State 设计

当前共享状态在：

```text
src/agent_scope/state.py
```

```python
class ResearchState(TypedDict, total=False):
    user_question: str
    research_goal: str
    tasks: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    notes: List[Dict[str, Any]]
    final_report: str
    logs: List[str]
```

这个设计刻意保持简单。后续加入 verifier、critic、supervisor 时，可以继续扩展：

```python
verified_claims: List[Dict[str, Any]]
critique: str
revision_notes: List[str]
evaluation: Dict[str, Any]
research_round: int
```

---

## 7. 后续扩展建议

### 下一步 A：加入 Verifier

把流程改成：

```text
planner → researcher → verifier → writer
```

Verifier 负责检查：

- 哪些 claim 没有 source id。
- 哪些 source 是搜索错误或低质量来源。
- 哪些 finding confidence 太低。

### 下一步 B：加入 Critic

把流程改成：

```text
planner → researcher → writer → critic → revision
```

Critic 负责找遗漏、过度推断和逻辑漏洞。

### 下一步 C：加入 Supervisor 条件循环

把流程改成：

```text
planner → researcher → verifier → should_continue?
                             ├── yes → researcher
                             └── no  → writer
```

这样就从线性 workflow 变成真正的 agentic graph。

---

## 8. 常见问题

### 1. 为什么不用很多 Agent？

因为第一版最重要的是跑通状态流和图结构。过早加入太多 Agent 会导致调试困难、成本高、结果不稳定。

### 2. 为什么要求 JSON 输出？

Planner 和 Researcher 的输出需要被后续节点读取。如果只输出自然语言，后面很难稳定解析，也很难做 verifier、supervisor 和 evaluation。

### 3. Tavily API Key 必须有吗？

推荐配置。当前 Tavily SDK 有可能支持 keyless mode，但会有服务限制。为了稳定运行，建议设置 `TAVILY_API_KEY`。

### 4. 能不能用 DeepSeek？

可以。推荐先用 `deepseek-chat`，不要一开始用 `deepseek-reasoner`。这个 MVP 依赖稳定的结构化 JSON 风格输出，`deepseek-chat` 更适合作为默认模型。
