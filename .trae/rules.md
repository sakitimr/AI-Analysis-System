# TRAE Project Rules — AI Analysis System

> 本规则文件用于指导 TRAE IDE 中的 AI 助手进行本项目开发。
> 遵循课题要求：深度使用 TRAE 等 AI 编程工具。

## 项目概述

AI 驱动的竞品分析 Agent 协作系统，基于 LangGraph 多 Agent 编排，
由 4 个专职 Agent 自动完成竞品分析全链路。

## 开发规范

### 代码风格
- Python 3.11+，PEP 8 标准
- Type hints 全覆盖
- docstring 用于所有公共方法
- 关键逻辑必须注释

### 架构原则
- 四层架构：UI → Orchestration → Agent/Storage → Infrastructure
- 关注点分离：Agent 之间仅通过 Pydantic Schema 通信
- 配置集中：config/settings.py 单一真相源

### AI 协作模式
- 人工决策：系统架构、技术选型、关键设计
- AI 执行：代码实现、测试、文档、Code Review
- 迭代方式：AI 生成 → 人工审核 → AI 修复

### 敏感信息
- API Key 通过 .env 管理，不纳入 Git
- 不在代码中硬编码任何凭证信息
