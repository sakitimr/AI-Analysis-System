"""Pre-collected sample data for offline/demo mode."""
from datetime import datetime

def get_sample_data():
    now = datetime.now().isoformat()
    return {
        "Cursor": {
            "competitor": "Cursor", "collected_at": now, "status": "success",
            "dimensions": {
                "功能对比": [
                    {"field": "code_completion", "value": "Multi-line AI code completion with full context awareness", "source_url": "https://cursor.com/features", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "chat_interface", "value": "AI Chat panel with code context, supports @-references", "source_url": "https://cursor.com/features", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "multi_file_editing", "value": "Composer mode allows editing multiple files simultaneously", "source_url": "https://cursor.com/blog/composer", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "agent_mode", "value": "Agent mode automates complex refactoring", "source_url": "https://cursor.com/features", "source_type": "official", "confidence": "medium", "accessed_at": now},
                    {"field": "model_selection", "value": "Supports Claude, GPT-4o, and custom models", "source_url": "https://docs.cursor.com/get-started/models", "source_type": "official", "confidence": "high", "accessed_at": now},
                ],
                "定价模型": [
                    {"field": "free_tier", "value": "Free tier: 2000 completions/month", "source_url": "https://cursor.com/pricing", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "pro_tier", "value": "$20/month for unlimited completions", "source_url": "https://cursor.com/pricing", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "business_tier", "value": "$40/user/month with admin controls and SSO", "source_url": "https://cursor.com/pricing", "source_type": "official", "confidence": "high", "accessed_at": now},
                ],
                "用户评价": [
                    {"field": "positive", "value": "Best-in-class AI code completion; users praise context awareness and speed", "source_url": "https://www.reddit.com/r/cursor/", "source_type": "community", "confidence": "medium", "accessed_at": now},
                    {"field": "negative", "value": "$20/month seen as expensive vs GitHub Copilot free tier; privacy concerns", "source_url": "https://news.ycombinator.com/item?id=40600000", "source_type": "community", "confidence": "medium", "accessed_at": now},
                ],
            },
            "sources": [
                {"url": "https://cursor.com/features", "title": "Cursor Features", "type": "official"},
                {"url": "https://cursor.com/pricing", "title": "Cursor Pricing", "type": "official"},
                {"url": "https://docs.cursor.com/get-started/models", "title": "Cursor Models", "type": "official"},
                {"url": "https://cursor.com/blog/composer", "title": "Cursor Composer", "type": "official"},
            ]
        },
        "GitHub Copilot": {
            "competitor": "GitHub Copilot", "collected_at": now, "status": "success",
            "dimensions": {
                "功能对比": [
                    {"field": "code_completion", "value": "Context-aware ghost text completions; NES for multi-location edits", "source_url": "https://github.com/features/copilot", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "chat_interface", "value": "Copilot Chat with @workspace context, supports GPT-4o and Claude", "source_url": "https://docs.github.com/en/copilot", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "multi_file_editing", "value": "Copilot Edits: multi-file changes with review", "source_url": "https://github.blog/changelog/2025-02-06-copilot-edits/", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "agent_mode", "value": "Copilot Agent mode (preview) for autonomous tasks", "source_url": "https://github.blog/2025-05-05-copilot-coding-agent/", "source_type": "official", "confidence": "medium", "accessed_at": now},
                    {"field": "model_selection", "value": "GPT-4o, Claude 3.5 Sonnet, Gemini 2.5 Pro, o4-mini", "source_url": "https://docs.github.com/en/copilot/about-github-copilot/ai-models", "source_type": "official", "confidence": "high", "accessed_at": now},
                ],
                "定价模型": [
                    {"field": "free_tier", "value": "Free: 2000 completions, 50 chat messages/month", "source_url": "https://github.com/features/copilot/plans", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "individual", "value": "$10/month or $100/year", "source_url": "https://github.com/features/copilot/plans", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "business", "value": "$19/user/month with org policies and IP indemnification", "source_url": "https://github.com/features/copilot/plans", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "enterprise", "value": "$39/user/month with custom model fine-tuning", "source_url": "https://github.com/features/copilot/plans", "source_type": "official", "confidence": "high", "accessed_at": now},
                ],
                "用户评价": [
                    {"field": "positive", "value": "Broad IDE support; Deep GitHub integration; Strong enterprise trust", "source_url": "https://www.g2.com/products/github-copilot/reviews", "source_type": "review", "confidence": "high", "accessed_at": now},
                    {"field": "negative", "value": "Can be slow in large projects; Context retrieval limited", "source_url": "https://www.reddit.com/r/github/", "source_type": "community", "confidence": "medium", "accessed_at": now},
                ],
            },
            "sources": [
                {"url": "https://github.com/features/copilot", "title": "GitHub Copilot", "type": "official"},
                {"url": "https://github.com/features/copilot/plans", "title": "Copilot Plans", "type": "official"},
                {"url": "https://docs.github.com/en/copilot", "title": "Copilot Docs", "type": "official"},
                {"url": "https://www.g2.com/products/github-copilot/reviews", "title": "G2 Reviews", "type": "review"},
            ]
        },
        "TRAE": {
            "competitor": "TRAE", "collected_at": now, "status": "success",
            "dimensions": {
                "功能对比": [
                    {"field": "code_completion", "value": "AI code completion powered by Doubao models, supports Chinese/English", "source_url": "https://www.trae.ai/", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "chat_interface", "value": "Built-in AI chat with code context and multi-turn conversation", "source_url": "https://www.trae.ai/features", "source_type": "official", "confidence": "high", "accessed_at": now},
                    {"field": "multi_file_editing", "value": "Workspace-level edits with Builder mode", "source_url": "https://www.trae.ai/features", "source_type": "official", "confidence": "medium", "accessed_at": now},
                    {"field": "agent_mode", "value": "Builder mode for autonomous project generation", "source_url": "https://www.trae.ai/features", "source_type": "official", "confidence": "medium", "accessed_at": now},
                    {"field": "model_selection", "value": "Doubao-Seed-2.0-lite (default), supports BYOK", "source_url": "https://www.trae.ai/docs", "source_type": "official", "confidence": "medium", "accessed_at": now},
                ],
                "定价模型": [
                    {"field": "free_tier", "value": "Free tier with Doubao model, limited daily usage", "source_url": "https://www.trae.ai/pricing", "source_type": "official", "confidence": "medium", "accessed_at": now},
                    {"field": "pro_tier", "value": "Pricing details not publicly available", "source_url": "https://www.trae.ai/pricing", "source_type": "official", "confidence": "low", "accessed_at": now},
                ],
                "用户评价": [
                    {"field": "positive", "value": "Free to use; Good Chinese language support; Clean UI; ByteDance backing", "source_url": "https://www.zhihu.com/topic/trae-ai", "source_type": "community", "confidence": "medium", "accessed_at": now},
                    {"field": "negative", "value": "Limited ecosystem vs VS Code; Smaller community; Model behind GPT/Claude", "source_url": "https://www.zhihu.com/topic/trae-ai", "source_type": "community", "confidence": "medium", "accessed_at": now},
                ],
            },
            "sources": [
                {"url": "https://www.trae.ai/", "title": "TRAE Official", "type": "official"},
                {"url": "https://www.trae.ai/features", "title": "TRAE Features", "type": "official"},
                {"url": "https://www.trae.ai/pricing", "title": "TRAE Pricing", "type": "official"},
                {"url": "https://www.zhihu.com/topic/trae-ai", "title": "TRAE Zhihu", "type": "community"},
            ]
        },
    }
