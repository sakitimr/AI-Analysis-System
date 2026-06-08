# 系统架构文档

> 字节跳动 CIS AI 全栈项目挑战 —— AI 驱动的竞品分析 Agent 协作系统

---

## 目录

1. [总体架构](#1-总体架构)
2. [四层架构详解](#2-四层架构详解)
3. [数据流与状态管理](#3-数据流与状态管理)
4. [DAG 任务流转](#4-dag-任务流转)
5. [关键技术决策](#5-关键技术决策)
6. [目录结构](#6-目录结构)

---

## 1. 总体架构

本系统采用四层架构设计，遵循关注点分离原则：

```
┌─────────────────────────────────────────────────────────────┐
│                    前端交互层 (UI Layer)                      │
│   Streamlit Dashboard                                       │
│   任务创建 | 实时监控 (DAG可视化) | 报告查看 | 溯源跳转        │
│   决策回放 | 人工修正 → 重新质检                              │
├─────────────────────────────────────────────────────────────┤
│                    服务编排层 (Orchestration Layer)           │
│   LangGraph StateGraph                                      │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│   │ Collector │→ │ Analyst  │→ │  Writer  │→ │    QC    │   │
│   │  Agent    │  │  Agent   │  │  Agent   │  │  Agent   │   │
│   └──────────┘  └──────────┘  └──────────┘  └────┬─────┘   │
│        ↑                                   fail │          │
│        └──────────── 打回修正 ◄──────────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                    知识 & 存储层 (Storage Layer)             │
│   Pydantic Schemas (竞品知识结构)  |  SQLite (WAL模式)       │
│   JSON 缓存 (离线模式)              |  报告导出 (Markdown)     │
├─────────────────────────────────────────────────────────────┤
│                    基础设施层 (Infrastructure Layer)         │
│   配置管理 (.env + settings.py)  |  日志 (Python logging)    │
│   异常处理 (try/except + tenacity) |  超时重试 (指数退避)    │
│   降级机制 (离线回退 + 3轮迭代上限)                          │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 层间通信协议

| 方向 | 协议 | 格式 |
|------|------|------|
| UI → Orchestration | HTTP REST (FastAPI) | JSON |
| Orchestration 内部 | LangGraph State Graph | TypedDict + Pydantic |
| Agent → Agent | WorkflowState 字段传递 | TypedDict 强类型 |
| Agent → LLM | ChatOpenAI SDK | OpenAI-compatible API |
| Schema 校验 | Pydantic runtime validation | Model Schema |

---

## 2. 四层架构详解

### 2.1 前端交互层

**技术选型**：Streamlit (v1.x)

**页面路由** (`src/ui/app.py`)：

| 页面 | 路由 | 功能 |
|------|------|------|
| 任务创建 | `/` 或 sidebar | 输入竞品名称、选择分析维度、启动分析 |
| 实时监控 | 自动切换 | DAG 执行流可视化、各 Agent 实时输出、Trace 数据展示 |
| 报告查看 | 完成后展示 | Markdown 渲染、溯源引用可点击跳转、下载 PDF |
| 决策回放 | 时间线组件 | 每个 Agent 决策过程 + 中间产物追溯 |

### 2.2 服务编排层

**技术选型**：LangGraph (StateGraph)

**核心文件**：
- `src/orchestration/state.py` — WorkflowState 定义
- `src/orchestration/graph.py` — 节点函数 + 图构建
- `src/orchestration/router.py` — 条件路由逻辑

**状态定义** (`WorkflowState`)：

```python
class WorkflowState(TypedDict, total=False):
    competitors: List[str]           # ["Cursor", "GitHub Copilot", "TRAE"]
    analysis_dimensions: List[str]   # ["功能对比", "定价模型", "用户评价", "SWOT分析"]
    collected_data: Optional[Dict]   # Collector 输出 (按竞品聚合的 DataPoint)
    analysis_result: Optional[Dict]  # Analyst 输出 (FeatureMatrix, SWOT, etc.)
    report: Optional[str]            # Writer 输出 (Markdown 完整报告)
    qc_result: Optional[Dict]        # QC 输出 (QCVerdict)
    qc_iteration: int                # 当前质检轮次
    max_iterations: int              # 最大重试次数（默认3）
    collection_hints: Optional[List] # 打回时携带的重采指令
    trace: List[dict]                # 全链路执行日志
    validation_warnings: List[dict]  # 数据校验警告
    status: str                      # "running" | "completed" | "completed_degraded" | "failed"
    error_message: str
```

**节点函数**（`src/orchestration/graph.py`）：

| 节点 | 函数 | 职责 |
|------|------|------|
| `collector` | `collector_node()` | 调用 CollectorAgent，填充 `collected_data` |
| `analyst` | `analyst_node()` | 调用 AnalystAgent，填充 `analysis_result` |
| `writer` | `writer_node()` | 调用 WriterAgent，填充 `report` |
| `qc` | `qc_node()` | 调用 QCAgent，填充 `qc_result`，触发路由 |

### 2.3 知识 & 存储层

**Pydantic Schemas** (`src/schema/competitive.py`)：

```
DataPoint (基本信息单元)
  ├── field: str          # 字段标识
  ├── value: str          # 提取的值
  ├── source_url: str     # 来源 URL
  ├── source_type: enum   # official | review | news | community | other
  ├── accessed_at: str    # 访问时间
  └── confidence: str     # high | medium | low

CollectedData (采集产物)
  ├── competitor: str
  ├── dimensions: Dict[str, List[DataPoint]]
  └── sources: List[Dict]

AnalysisResult (分析产物)
  ├── competitors: List[str]
  ├── feature_matrix: FeatureMatrix
  │   ├── features: List[str]        # 功能维度列表
  │   └── matrix: List[FeatureRow]   # 每个功能×每个竞品的评分(0-3)+notes+source
  ├── swot: List[SWOTEntry]          # 每个竞品的 S/W/O/T
  ├── pricing_analysis: List[PricingPlan]
  ├── user_sentiment: List[SentimentProfile]
  │   ├── positive_themes / negative_themes
  │   └── sentiment_score: float (-1.0 ~ 1.0)
  └── key_insights: List[str]

FinalReport (撰写产物)
  ├── title + content (Markdown)
  ├── word_count + source_count
  └── mermaid_diagrams: List[str]
```

**SQLite 存储** (`src/storage/database.py`)：

WAL 模式，两张表：
- `tasks` — 任务记录（competitors, dimensions, status, report_path）
- `runs` — 运行记录（task_id, status, duration, tokens, qc_iterations, trace）

### 2.4 基础设施层

**配置管理** (`config/settings.py`)：
- 环境变量驱动（.env 文件，不纳入 Git）
- 全局配置常量：LLM_TEMPERATURE=0.3, LLM_MAX_TOKENS=4096, MAX_QC_ITERATIONS=3
- 路径管理：DB_PATH, CACHE_DIR, REPORT_DIR

**Agent 基类** (`src/agents/base.py`)：
- `invoke(prompt)` — 单次 LLM 调用，自动记录 trace
- `safe_invoke_json(prompt)` — JSON 输出 + 自动修复（最多2次重试）
- `_invoke_with_retry(prompt)` — tenacity 指数退避重试（3次，2s→4s→8s）
- `get_trace(step, input_summary, output_summary)` — 聚合所有调用记录

---

## 3. 数据流与状态管理

### 3.1 主链路数据流

```
User Input (竞品名称 + 分析维度)
    │
    ▼
Collector: competitors[] × dimensions[] → search queries[10+]
    │  DuckDuckGo API → HTML抓取 → LLM结构化提取
    ▼
collected_data: Dict[str, CollectedData]
    │  每个竞品包含4个维度的 DataPoint[]
    ▼
Analyst: collected_data → LLM分析
    │  功能矩阵(0-3评分) + SWOT + 定价 + 情感 + 洞察
    ▼
analysis_result: AnalysisResult (Pydantic)
    │
    ▼
Writer: analysis_result → Markdown 模板装配
    │  章节组装 + 来源注入 + Mermaid图表
    ▼
report: str (完整 Markdown 报告)
    │
    ▼
QC: report → 规则校验 + LLM校验 + 溯源校验
    │
    ├── pass → 输出最终报告
    └── fail → qc_router 打回对应 Agent → 重新执行
```

### 3.2 数据流转协议

Agent 间通过 `WorkflowState` 字段传递结构化数据。Graph 中的 `_to_dict()` 辅助函数将 Pydantic 模型序列化，下游节点重新构造：

```python
# writer_node 中的示例
analysis = AnalysisResult(**state.get("analysis_result", {}))
cd = {c: _to_dict(d) for c, d in state.get("collected_data", {}).items()}
report = wri.write_report(analysis, cd)
```

这保证了非自然语言通信的要求——每个 Agent 的输出是强类型数据结构，而非自由文本。

---

## 4. DAG 任务流转

### 4.1 正常流程

```
collector → analyst → writer → qc → END (pass)
```

### 4.2 反馈闭环流程

```
qc → retry_router → retry_collector → analyst → writer → qc
                  → retry_analyst → writer → qc
                  → retry_writer → qc
```

**路由器逻辑** (`src/orchestration/router.py`)：

```python
def qc_router(state: WorkflowState) -> str:
    # 1. 检查 QC 是否通过
    if qc_result["pass_"]:
        return "end"
    
    # 2. 检查是否超过最大迭代次数
    if iteration >= max_iterations:
        state["status"] = "completed_degraded"  # 降级输出
        return "end"
    
    # 3. 按问题类型路由
    if collector_issues:
        state["collection_hints"] = hints  # 携带重采指令
        return "retry_collector"
    if analyst_issues:
        return "retry_analyst"
    return "retry_writer"
```

**打回重采机制**：

当 QC 检测到采集数据不足时：
1. 设置 `state["collection_hints"]`，包含缺失字段和目标竞品
2. Collector 的 `recollect()` 方法仅重采缺失维度，而非全量重新采集
3. 节省 API 调用，提高效率

### 4.3 降级策略

| 场景 | 策略 |
|------|------|
| QC 3轮不通过 | `completed_degraded`，标记报告质量但依然输出 |
| LLM 调用失败 | tenacity 重试3次后抛出异常 |
| JSON 解析失败 | 2次重试（含LLM自修复）后抛异常 |
| 搜索无结果 | 回退到 sample_data 离线数据 |
| API 不可用 | 离线模式完整演示 |

---

## 5. 关键技术决策

### 5.1 为何选择 LangGraph 而非 CrewAI

| 维度 | LangGraph | CrewAI | 选择理由 |
|------|-----------|--------|---------|
| DAG支持 | ✅ StateGraph + conditional edges | ❌ 线性对话 | 反馈闭环需要条件路由 |
| 结构化通信 | ✅ State 传递 TypedDict | ❌ 自然语言对话 | 课题明确要求非纯语言通信 |
| Checkpoint | ✅ 原生支持 | ❌ 无 | 决策回放需求 |
| Trace | ✅ 节点级日志 | ⚠️ 有限 | 可观测性要求 |
| 可控性 | ✅ 显式 graph 定义 | ⚠️ 黑盒 | 需要精确控制流转 |

### 5.2 为何选择 Pydantic 而非 dataclasses

| 维度 | Pydantic | dataclasses | 选择理由 |
|------|----------|-------------|---------|
| 运行时校验 | ✅ model_validate | ❌ 无 | 保证 Schema 一致性 |
| 序列化 | ✅ model_dump() | ❌ 手动 | Agent 间传递需要 |
| JSON Schema | ✅ 自动生成 | ❌ 无 | API 文档自动生成 |
| 默认值 | ✅ Field() | ⚠️ field() | 容错需要的降级值 |

### 5.3 为何选择 DuckDuckGo 而非 Google

| 维度 | DuckDuckGo | Google Custom Search | 选择理由 |
|------|-----------|---------------------|---------|
| API Key | ❌ 不需要 | ✅ 需要付费 | 零成本 |
| 合规性 | ✅ 公开 API | ⚠️ 需遵守 ToS | 评分含合规 |
| 中文搜索 | ⚠️ 一般 | ✅ 优秀 | 通过中英文混合查询折中 |

### 5.4 为何选择 Streamlit 而非 Gradio/React

| 维度 | Streamlit | Gradio | React |
|------|-----------|--------|-------|
| 开发速度 | ✅ 纯Python，分钟级 | ✅ 纯Python | ❌ JS + HTML |
| 与后端集成 | ✅ 同进程，共享状态 | ⚠️ 队列通信 | ❌ 需要 API 层 |
| 演示效果 | ✅ 美观，开箱即用 | ⚠️ 偏ML场景 | ✅ 极致可控 |
| 学习成本 | ✅ 极低 | ✅ 低 | ❌ 高 |

---

## 6. 目录结构

```
competitive-analysis-agent/
├── config/
│   └── settings.py              # 全局配置（LLM参数、路径、常量）
├── src/
│   ├── agents/                  # Agent 实现
│   │   ├── base.py              # BaseAgent（LLM交互、Trace、重试）
│   │   ├── collector.py         # CollectorAgent（搜索+抓取+提取）
│   │   ├── analyst.py           # AnalystAgent（矩阵+SWOT+情感+定价）
│   │   ├── writer.py            # WriterAgent（报告模板+引用注入）
│   │   └── qc.py                # QCAgent（规则+LLM+溯源三层校验）
│   ├── orchestration/           # LangGraph 编排
│   │   ├── state.py             # WorkflowState (TypedDict)
│   │   ├── graph.py             # 节点函数 + StateGraph 构建
│   │   └── router.py            # QC 条件路由（反馈闭环核心）
│   ├── schema/                  # Pydantic 数据模型
│   │   ├── competitive.py       # 竞品知识 Schema (CollectedData, AnalysisResult, etc.)
│   │   ├── messages.py          # Agent间消息协议 (AgentMessage, QCVerdict, TraceEntry)
│   │   └── validators.py        # Schema 校验器 + JSON 安全解析
│   ├── tools/                   # 外部工具
│   │   ├── search.py            # DuckDuckGo 搜索（含中文编码处理）
│   │   ├── web_scraper.py       # 网页抓取（HTML→Markdown）
│   │   ├── citation.py          # CitationManager（引用管理）
│   │   └── sample_data.py       # 离线预采集数据（演示/降级）
│   ├── storage/                 # 持久化
│   │   ├── database.py          # SQLite CRUD (WAL模式)
│   │   └── models.py            # TaskRecord / RunRecord (dataclass)
│   ├── api/                     # FastAPI 后端
│   │   ├── main.py              # FastAPI 入口 (CORS, lifespan)
│   │   └── routes.py            # REST路由 (tasks CRUD + async run)
│   └── ui/                      # Streamlit 前端
│       └── app.py               # 4 页面交互 UI
├── tests/                       # 单元测试
│   ├── test_collector.py
│   ├── test_analyst.py
│   ├── test_writer.py
│   ├── test_qc.py
│   └── test_orchestration.py
├── docs/                        # 文档
│   ├── ARCHITECTURE.md          # 本文件
│   ├── AGENT_ROLES.md           # Agent角色与协议
│   ├── DEPLOYMENT.md            # 部署说明
│   ├── COMPLIANCE.md            # 合规声明
│   └── SCORING_MATRIX.md        # 评分规则对照
├── data/                        # 数据目录
│   ├── tasks.db                 # SQLite 数据库
│   ├── cache/                   # 采集缓存
│   └── reports/                 # 报告导出
├── run_full_pipeline.py         # CLI 入口（离线/在线/API模式）
├── requirements.txt             # 依赖
├── README.md                    # 项目说明
├── .env.example                 # 环境变量模板
└── .gitignore                   # Git 忽略规则
```

---

> 📅 文档版本：v2.0 | 2026-06-04  
> 🔵 贾维斯 (J.A.R.V.I.S.)
