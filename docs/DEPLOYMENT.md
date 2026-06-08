# 部署说明

> 字节跳动 CIS AI 全栈项目挑战

---

## 系统要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.10 | 3.11+ |
| pip | 21.0+ | 最新 |
| 操作系统 | Windows 10+ / macOS 12+ / Linux | 任意 |
| 磁盘空间 | 200 MB | 500 MB |
| 内存 | 4 GB | 8 GB |

---

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/sakitimr/AI-Analysis-System.git
cd AI-Analysis-System
```

### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入 Doubao API 配置：

```env
DOUBAO_API_KEY=ark-your-api-key-here
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_MODEL=doubao-seed-2.0-lite-251015
```

### 5. 验证安装

```bash
python -m pytest tests/ -v
```

预期：15/15 测试通过。

---

## 运行模式

### 模式 1：CLI 离线模式（推荐用于演示）

使用预采集数据，无需网络搜索，最快最稳定：

```bash
python run_full_pipeline.py
```

输出：
- 终端显示全链路执行日志
- `data/reports/analysis_YYYYMMDD_HHMMSS.md` 完整报告

### 模式 2：CLI 在线模式

实时搜索网络数据：

```bash
python run_full_pipeline.py --online
```

⚠️ 需要稳定网络连接，耗时约 8-15 分钟（含 3 竞品搜索+抓取）。

### 模式 3：自定义分析

```bash
python run_full_pipeline.py --competitors "飞书,钉钉,企业微信" --dimensions "功能对比,定价模型"
```

### 模式 4：Web UI

```bash
streamlit run src/ui/app.py
```

浏览器打开 `http://localhost:8501`

功能页面：
1. **任务创建** — 输入竞品和维度，启动分析
2. **实时监控** — DAG 执行状态可视化
3. **报告查看** — Markdown 渲染，溯源可点击
4. **决策回放** — 时间线展示 Agent 决策过程

### 模式 5：API 服务

```bash
# 启动 API
python run_full_pipeline.py --api

# 或直接使用 uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

API 文档：`http://localhost:8000/docs`

端点：
- `POST /api/tasks` — 创建分析任务
- `GET /api/tasks` — 任务列表
- `GET /api/tasks/{id}` — 任务详情
- `GET /api/tasks/{id}/report` — 获取报告
- `GET /api/health` — 健康检查

---

## 目录说明

```
competitive-analysis-agent/
├── config/settings.py         # 配置文件（可修改 LLM 参数）
├── src/                       # 源代码
│   ├── agents/                # 4 个 Agent 实现
│   ├── orchestration/         # LangGraph 编排
│   ├── schema/                # Pydantic 数据模型
│   ├── tools/                 # 搜索/抓取/引用工具
│   ├── storage/               # SQLite 持久化
│   ├── api/                   # FastAPI 后端
│   └── ui/                    # Streamlit 前端
├── tests/                     # 单元测试
├── docs/                      # 项目文档
├── data/                      # 运行时数据（自动创建）
│   ├── tasks.db               # SQLite 数据库
│   ├── cache/                 # 搜索缓存
│   └── reports/               # 报告导出
└── run_full_pipeline.py       # CLI 入口
```

---

## 常见问题

### Q: 提示 "module not found" 怎么办？

```bash
pip install -r requirements.txt
```

### Q: API 调用超时怎么办？

增大 `.env` 或 `config/settings.py` 中的 `LLM_TIMEOUT`：

```python
LLM_TIMEOUT = 180  # 增加到 180 秒
```

### Q: 搜索无结果？

1. 检查网络连接
2. 使用离线模式：`python run_full_pipeline.py`（不加 --online）
3. 检查 `SEARCH_PROXY` 环境变量是否需要设置代理

### Q: 如何切换模型？

修改 `.env` 中的 `DOUBAO_MODEL`：

```env
DOUBAO_MODEL=ep-20260514111325-xjmj7
```

---

## 开发指南

### 运行测试

```bash
# 全部测试
python -m pytest tests/ -v

# 单个 Agent 测试
python -m pytest tests/test_collector.py -v
```

### 代码风格

- 遵循 PEP 8
- Type hints 全覆盖
- 关键逻辑含注释

### 添加新 Agent

1. 在 `src/agents/` 创建新文件，继承 `BaseAgent`
2. 在 `src/schema/` 定义输入/输出 Pydantic Model
3. 在 `src/orchestration/graph.py` 添加节点函数
4. 如需路由，在 `src/orchestration/router.py` 添加条件

---

> 📅 文档版本：v2.0 | 2026-06-04  
> 🔵 贾维斯 (J.A.R.V.I.S.)
