# AI 驱动的竞品分析 Agent 协作系统

> 字节跳动集团信息系统部（CIS）AI 全栈项目挑战  
> 课题：AI 驱动的竞品分析 Agent 协作系统  
> 周期：2026.05.20 – 2026.06.10  
> 模型：Doubao-Seed-2.0-lite

---

## 项目概述

一个基于 LangGraph 的多 Agent 协作竞品分析系统，模拟"数字调研小组"，由 4 个专职 Agent（采集/分析/撰写/质检）自动完成从公开信息采集到结构化竞品报告的全链路产出，通过 Agent 间交叉审查与反馈机制实现自我校验。

### 分析对象

| 竞品 | 开发商 | 定位 |
|------|--------|------|
| **Cursor** | Anysphere | AI-first IDE，基于 VS Code Fork |
| **GitHub Copilot** | Microsoft / GitHub | AI 代码补全 + Chat，IDE 插件形态 |
| **TRAE** | 字节跳动 | 国产 AI IDE，深度集成豆包模型 |

### 核心特性

- 🔄 **真实反馈闭环**：QC Agent 打回→采集/分析/撰写重做，最多 3 轮，非伪闭环
- 📊 **结构化通信**：Agent 间通过 Pydantic Schema + LangGraph State 传递，非自然语言
- 🔗 **完整信息溯源**：每条结论标注数据来源，支持一键跳转
- 📈 **可观测性**：每个 Agent 的 Prompt、输入、输出、Token 消耗、耗时全记录
- 🌐 **端到端全链路**：数据采集 → Agent 编排 → 知识存储 → API → 前端交互

---

## 快速开始

### 环境要求

- Python 3.10+
- pip

### 安装

```bash
cd AI-Analysis-System
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env: 填入 DOUBAO_API_KEY
```

### 运行

```bash
# CLI 全链路分析（离线模式，使用预采集数据，~5分钟）
python run_full_pipeline.py

# 在线搜索模式
python run_full_pipeline.py --online

# 自定义竞品和维度
python run_full_pipeline.py --competitors "飞书,钉钉,企业微信" --dimensions "功能对比,定价模型"

# 启动 Web 前端
streamlit run src/ui/app.py

# 启动 API 服务
uvicorn src.api.main:app --reload --port 8000
# API 文档: http://localhost:8000/docs

# 运行测试
python -m pytest tests/ -v
```

---

## 系统架构

```
前端交互层:  Streamlit (报告查看/溯源跳转/决策回放/人工修正)
     ↕ REST API (FastAPI + async)
服务编排层:  LangGraph StateGraph (4 Agent + 条件路由 + 反馈闭环)
     ↕ Pydantic Schemas (结构化消息)
Agent 层:    Collector / Analyst / Writer / QC
     ↕ SQLite WAL 持久化
存储层:      tasks + runs 记录 | 报告导出
```

### Agent 角色

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **Collector** | 多源搜索+网页抓取+结构化提取 | 竞品名称 + 分析维度 | CollectedData |
| **Analyst** | 功能矩阵+SWOT+情感+定价分析 | CollectedData | AnalysisResult |
| **Writer** | Markdown 报告组装+引用注入 | AnalysisResult | FinalReport |
| **QC** | 五层质量校验（规则+LLM+溯源） | 全链路产物 | QCVerdict |

### DAG 任务流转

```
collector → analyst → writer → qc
                                  ├── pass → END
                                  └── fail → retry_router
                                               ├── retry_collector → ...
                                               ├── retry_analyst → ...
                                               └── retry_writer → ...
                                               └── max_iterations → END (降级)
```

---

## 技术栈

| 技术 | 用途 | 选型理由 |
|------|------|---------|
| **LangGraph** | 多 Agent 编排 | DAG + 条件路由，天然适配反馈闭环 |
| **Doubao-Seed-2.0-lite** | LLM 推理 | 课题提供，字节跳动自研模型 |
| **FastAPI** | 后端 API | 异步高性能 + 自动 OpenAPI 文档 |
| **Pydantic** | Schema 定义 + 校验 | 运行时强类型校验，LangGraph 原生支持 |
| **Streamlit** | 前端交互 | 纯 Python，快速原型，演示效果好 |
| **SQLite** | 任务持久化 | 零配置，WAL 模式，满足数据规模 |
| **DuckDuckGo** | 网络搜索 | 免费，合规友好 |

---

## 项目文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构详解 |
| [AGENT_ROLES.md](docs/AGENT_ROLES.md) | Agent 角色与通信协议 |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | 部署说明 |
| [COMPLIANCE.md](docs/COMPLIANCE.md) | 合规声明 |
| [SCORING_MATRIX.md](docs/SCORING_MATRIX.md) | 评分规则逐项对照 |

---

## 项目状态

- ✅ 四个 Agent 全部开发完成
- ✅ LangGraph 编排 + 反馈闭环验证通过
- ✅ FastAPI + Streamlit 前后端联动
- ✅ 单元测试全覆盖（15/15 通过）
- ✅ 全链路 E2E 测试通过（~8分钟，3 竞品完整报告）
- ✅ 离线模式（API 不可用时完整演示）

---

## 性能数据

| 指标 | 数值 |
|------|------|
| 全链路耗时（3 竞品） | ~8 分钟 |
| 生成报告字数 | ~20,000 字 |
| 信息来源链接 | 10-12 个 |
| QC 迭代轮次 | 1-3 轮 |
| Token 消耗 | ~25,000 tokens/次 |
| 测试用例 | 15/15 通过 |

---

> 📅 2026-06-04 | 🔵 J.A.R.V.I.S.
