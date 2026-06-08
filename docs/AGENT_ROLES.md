# Agent 角色与通信协议

> 字节跳动 CIS AI 全栈项目挑战

---

## 目录

1. [角色总览](#1-角色总览)
2. [CollectorAgent](#2-collectoragent)
3. [AnalystAgent](#3-analystagent)
4. [WriterAgent](#4-writeragent)
5. [QCAgent](#5-qcagent)
6. [Agent 间通信协议](#6-agent-间通信协议)
7. [反馈闭环协议](#7-反馈闭环协议)

---

## 1. 角色总览

| Agent | 文件 | 职责 | 外部访问 | 输出 Schema |
|-------|------|------|---------|------------|
| Collector | `src/agents/collector.py` | 多源搜索+网页抓取+结构化数据提取 | ✅ 搜索网络 | CollectedData |
| Analyst | `src/agents/analyst.py` | 功能对比矩阵、SWOT、用户情感、定价分析 | ❌ 仅消费采集数据 | AnalysisResult |
| Writer | `src/agents/writer.py` | Markdown 报告组装、引用注入、Mermaid图表 | ❌ 仅格式化输出 | FinalReport |
| QC | `src/agents/qc.py` | 规则校验、LLM 一致性检查、溯源验证 | ❌ 仅检查不修改 | QCVerdict |

所有 Agent 继承 `BaseAgent` (`src/agents/base.py`)，共享 LLM 调用、Trace、异常重试等公共能力。

### 1.1 Agent 设计原则

1. **单一职责**：每个 Agent 只做一件事，职责边界明确
2. **数据驱动**：输入/输出均为结构化 Pydantic Model，非自由文本
3. **可观测**：每次 LLM 调用的 prompt、输入、输出、token、耗时均记录
4. **容错降级**：每个 Agent 有失败回退策略

---

## 2. CollectorAgent

### 2.1 职责

根据竞品名称 × 分析维度，多源搜索并抓取公开信息，产出结构化数据。

### 2.2 工作流程

```
competitors[] × dimensions[]
    │
    ▼
[1] 查询生成 (_gen_queries)
    ├── Phase 1: 硬编码模板（已知维度: 功能对比/定价模型/用户评价/SWOT分析）
    └── Phase 2: LLM 自适应生成（未知维度，前瞻性设计）
    │
    ▼
[2] 多源搜索 (search_web)
    └── DuckDuckGo API → 每个 query 最多返回 10 条
    │
    ▼
[3] 网页抓取 (scrape_page)
    └── 对前 3 条结果抓取页面正文 → 截断至 8000 chars
    │
    ▼
[4] LLM 结构化提取 (_extract_with_llm)
    ├── Prompt: "从搜索结果中提取结构化信息"
    ├── 输出格式: JSON { "dimensions": { "维度": [{ "field": "...", "value": "...", "source_url": "...", ... }] }, "sources": [...] }
    └── 约束: "ONLY use information from provided search results. NEVER invent data."
    │
    ▼
CollectedData (Pydantic)
```

### 2.3 关键设计

| 特性 | 实现 |
|------|------|
| 分批采集 | 每个竞品独立采集，竞品间延迟 3s |
| 内容优先 | 优先使用 page_content（完整正文），降级使用 snippet |
| 空洞处理 | 无搜索结果时返回 `status: "insufficient_data"` |
| 精准重采 | `recollect()` 仅重采 QC 打回的维度 |
| 幻觉抑制 | Prompt 强制 "ONLY use information from provided search results" |

### 2.4 Trace 示例

```json
{
  "agent": "collector",
  "step": "collect",
  "input_summary": "3 competitors",
  "output_summary": "3 result sets",
  "calls": 4,
  "total_tokens_input": 8500,
  "total_tokens_output": 3200,
  "total_duration_ms": 45000,
  "status": "success"
}
```

---

## 3. AnalystAgent

### 3.1 职责

对采集数据进行聚合、对比、SWOT 分析，产出结构化分析结果。

### 3.2 工作流程

```
CollectedData { competitor → dimensions → DataPoint[] }
    │
    ▼
[1] 功能对比矩阵 (_build_feature_matrix)
    ├── 提取功能特征 (_extract_features)
    │   ├── 从 collected dimensions 提取 field 名称
    │   └── 回退: 8 个预设特征（代码补全、Chat对话、多文件编辑...）
    ├── 评分 (_score_features_llm)
    │   ├── 主路径: LLM 数据驱动评分 0-3
    │   │   - 0 = 不可用/无证据
    │   │   - 1 = 基础/有限支持
    │   │   - 2 = 良好/有竞争力
    │   │   - 3 = 业界领先
    │   └── 降级路径: heuristic 基于数据详度评分
    │       - 无数据 → 0, 简短数据 → 1, 中等 → 2, 丰富 → 3
    └── 构建 FeatureRow[] (含 notes 和数据引用)
    │
    ▼
[2] SWOT 分析 (_gen_swot)
    ├── 主路径: LLM 基于全量数据生成 S/W/O/T（每象限 ≥3 项）
    ├── 降级路径: heuristic 基于 confidence/field 关键词
    └── 数据驱动: 仅基于采集数据，不自行编造
    │
    ▼
[3] 用户情感分析 (_analyze_sentiment)
    └── LLM 分析 → positive_themes + negative_themes + sentiment_score (-1~1)
    │
    ▼
[4] 定价分析 (_analyze_pricing)
    └── 从采集数据提取 → tier (free/pro/enterprise) + price + source_url
    │
    ▼
[5] 关键洞察 (_gen_insights)
    └── LLM 生成 3-5 条全局洞察
    │
    ▼
AnalysisResult (Pydantic)
```

### 3.3 关键设计

| 特性 | 实现 |
|------|------|
| 不访问外部 | 约束：仅消费 Collector 产出，无法直接搜索 |
| 双轨评分 | LLM 评分 → heuristic 降级，故障自动切换 |
| SWOT 容错 | LLM 失败 → heuristic 基于 confidence/关键词填充 |
| 上下文管理 | 每个竞品独立分析，避免超长上下文 |
| 数据驱动 | `_build_competitor_context()` 编译全量数据供 LLM 分析 |

---

## 4. WriterAgent

### 4.1 职责

将分析结果按 8 章节模板组装成完整 Markdown 报告，注入溯源引用。

### 4.2 报告结构

```
# 竞品分析报告
## 1. 执行摘要 (LLM 生成 2-3 段中文摘要)
## 2. 竞品概览 (表格: 竞品|开发商|定位|目标用户)
## 3. 核心功能对比矩阵 (表格: 功能|竞品A|竞品B|竞品C|说明)
## 4. 定价模型对比 (表格: 竞品|层级|价格)
## 5. 用户评价分析 (每竞品: 得分 + 正面/负面主题)
## 6. SWOT 分析 (每竞品: 优势|劣势 + 机会|威胁 表格)
## 7. 结论与建议 (LLM 生成 2-3 段中文结论 + 选型建议)
## 8. 数据来源 (编号列表，可点击跳转)
## 局限性声明
```

### 4.3 引用注入

每个数据来源在报告末尾自动收集：

```python
def _collect_sources(self, collected):
    # 遍历所有 collected_data，去重收集来源
    # 输出格式: 1. [标题](URL) -- *类型*
```

### 4.4 关键设计

| 特性 | 实现 |
|------|------|
| 模板驱动 | TEMPLATE 常量定义报告骨架，`str.format()` 填充 |
| LLM 增强 | 执行摘要和结论由 LLM 生成深度内容 |
| 自动采集 | 来源链接从 collected_data 自动提取去重 |
| 中文化 | 全中文报告输出 |

---

## 5. QCAgent

### 5.1 职责

五层校验确保报告质量，产出结构化裁决，驱动真实反馈闭环。

### 5.2 校验层次

```
[1] 章节完整性 (_check_completeness)
    └── 规则: 检查 8 个必要章节是否全部存在
    └── severity: critical → target_agent: writer

[2] 来源校验 (_check_sources)
    └── 规则: 正则提取 [N](url) 引用
    └── severity: critical → target_agent: writer

[3] 占位符检查 (_check_placeholders)
    └── 规则: 检查 [TODO]、[待补充]、[TBD]、[PLACEHOLDER]
    └── severity: minor → target_agent: writer

[4] 内容长度检查 (_check_word_count)
    └── 规则: 功能对比/定价/用户评价 章节 < 50 chars 视为不足
    └── severity: major → target_agent: writer

[5] LLM 语义校验 (_llm_check)
    └── 中文 Prompt: 检查数据矛盾、逻辑不一致、引用遗漏
    └── severity: critical|major|minor → target_agent: writer
```

### 5.3 裁决结构 (QCVerdict)

```python
class QCVerdict(BaseModel):
    qc_id: str                    # 唯一标识
    pass_: bool                   # 是否通过
    overall_score: float          # 0.0 ~ 1.0
    checks: Dict[str, Any]        # 各维度得分
    issues: List[Dict]            # 问题列表，每个含:
    │   ├── severity: "critical" | "major" | "minor"
    │   ├── section: str          # 问题所属章节
    │   ├── description: str      # 问题描述
    │   ├── target_agent: str     # 打回目标
    │   └── suggestion: str       # 修复建议
    suggestions: List[str]
    iteration: int                # 当前轮次
```

### 5.4 评分算法

```python
score = max(0.0, 1.0 - (critical*3 + major*2 + total_issues*0.5) / 10)
```

---

## 6. Agent 间通信协议

### 6.1 消息结构 (AgentMessage)

```python
class AgentMessage(BaseModel):
    message_id: str          # 唯一消息 ID
    agent_from: str          # 发送方 Agent
    agent_to: str            # 接收方 Agent
    message_type: MessageType  # pass | reject | correction | query
    timestamp: str           # ISO 时间戳
    payload: Any             # 结构化数据体
    trace_id: str            # 关联全链路 ID
    iteration: int           # 反馈闭环轮次
    metadata: Dict[str, Any] # 扩展元数据
```

### 6.2 通信方式

Agent 间**不直接发送消息**，而是通过 LangGraph StateGraph 的共享 State 传递：

```
Agent A 产出 Pydantic Model
  → model_dump() 写入 WorkflowState["xxx_result"]
    → Graph 自动传递给 Agent B
      → Agent B 读取 state["xxx_result"] → Pydantic(**data)
```

这确保了：
- **结构化通信**：dict 而非自由文本
- **可追溯**：每次写入/读取都有 graph 节点标记
- **可回滚**：LangGraph checkpoint 机制保存中间状态

### 6.3 与 function calling 的对应关系

| Function Calling 概念 | 本系统实现 |
|----------------------|-----------|
| function 定义 | Pydantic Schema 定义 |
| function 调用 | Agent 产出 model_dump() |
| function 返回 | 下游 Agent 读取 Pydantic(**data) |
| 参数校验 | Pydantic runtime validation |
| 错误处理 | safe_json_parse + 重试机制 |

---

## 7. 反馈闭环协议

### 7.1 闭环流程

```
qc → 产出 QCVerdict
  │
  ├── pass_=True → END
  │
  └── pass_=False → qc_router
       │
       ├── iteration >= max (3) → END (completed_degraded)
       │
       └── 按 issue.target_agent 路由:
            ├── "collector" → collector_node (携带 collection_hints)
            ├── "analyst"  → analyst_node
            └── "writer"   → writer_node
```

### 7.2 打回消息结构

当 QC 检测到采集问题，打回 Collector：

```python
state["collection_hints"] = [
    {
        "section": "定价模型",
        "target_competitor": "Cursor",
        "description": "缺少企业版定价信息",
        "severity": "major",
        "suggestion": "搜索 Cursor enterprise pricing 2025"
    }
]
```

Collector 收到后仅重采指定维度：

```python
def recollect(self, competitor, dimensions, hints):
    failed_dims = list(set(h.get("section", d) for h in hints for d in dimensions))
    return self._collect_single(competitor, failed_dims or dimensions)
```

### 7.3 真实闭环验证（2026-06-03 测试）

```
Iteration 1: QC 得分 0.40 → 发现问题 → 打回 Writer
Iteration 2: QC 得分 0.65 → 仍有问题 → 打回 Writer
Iteration 3: 达到上限 → END (completed_degraded)
```

验证标准：
- ✅ QC 能识别问题并打回
- ✅ 打回后针对性重做（非全量重跑）
- ✅ 重做后输出有可验证改善（得分逐轮上升）
- ✅ 达到上限后降级输出（非伪闭环）

---

> 📅 文档版本：v2.0 | 2026-06-04
> 🔵 贾维斯 (J.A.R.V.I.S.)
