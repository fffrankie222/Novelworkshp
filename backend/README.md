# NovelWorkshop 后端

网文写作多 Agent 系统 — FastAPI 后端服务

## 快速启动（Windows）

### 方式一：一键启动
```cmd
双击 start.bat
```

### 方式二：手动启动
```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

启动后访问：
- API 服务：http://localhost:8000
- 交互文档：http://localhost:8000/docs

## 模型配置

当前配置双 Provider：

| 任务类型 | 主模型 | 备用模型 |
|---------|--------|---------|
| 世界观/角色（高阶创意） | 🔥 豆包 Pro 32K | DeepSeek |
| 大纲/审核（强推理） | 🔥 豆包 Pro 32K | DeepSeek |
| 初稿/润色（量大） | DeepSeek | 🔥 豆包 Pro 32K |
| 人物对话 | 🔥 豆包 Pro 32K | DeepSeek |
| 摘要/轻量任务 | DeepSeek | 🔥 豆包 Pro 32K |

修改 `config/model_config.json` 可调整模型分配。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/books | 创建新书 |
| GET | /api/books | 书籍列表 |
| POST | /api/books/{id}/workflow/novel-setup | 启动新书建立 |
| POST | /api/books/{id}/workflow/chapter-production | 启动章节生产 |
| POST | /api/books/{id}/workflow/revision | 启动修订润色 |
| GET | /api/books/{id}/chapters | 章节列表 |
| GET | /api/books/{id}/state/characters | 角色状态 |
| GET | /api/books/{id}/state/hooks | 伏笔账本 |
| GET | /api/books/{id}/state/timeline | 时间线 |

## 项目结构

```
backend/
├── main.py              # FastAPI 入口
├── start.bat            # Windows 一键启动
├── config/              # 配置（模型分级、环境变量）
├── app/
│   ├── agents/          # 8 个 Agent + 基类
│   ├── api/             # 14 个 API 端点
│   ├── llm/             # 双 Provider LLM 客户端 + 路由
│   ├── models/          # 7 个 Pydantic 数据模型
│   ├── prompts/         # 8 个 Agent System Prompt
│   ├── tools/           # 上下文组装、状态更新等工具
│   └── workflows/       # Workflow 引擎 + 4 条流水线
└── data/workspaces/     # 运行时书籍工作区
```
