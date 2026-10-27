# NovelWorkshop v3.2 — 网文写作多 Agent 系统

## 前置要求
- **Python 3.11+**（推荐 3.12）
- **Node.js 18+**（推荐 20 LTS）
- Windows 10/11，已配置好 API Key（见下方说明）

## 一键启动（Windows）

**双击运行 `start.bat`**

它会自动：安装后端依赖 → 安装前端依赖 → 启动后端(8000) + 前端(5173)

## 手动启动

**终端 1 — 后端：**
```cmd
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 — 前端：**
```cmd
cd frontend
npm install
npm run dev
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

## API Key 配置

复制 `backend/.env.example` 为 `backend/config/.env`（或设置环境变量），填入你自己的 Key：
- **DeepSeek**：`DEEPSEEK_API_KEY`（DeepSeek 开放平台申请）
- **火山引擎豆包-pro**：`VOLCANO_API_KEY` 与接入点 `VOLCANO_PRO_ENDPOINT`（火山引擎方舟控制台获取）

> v4.7 起密钥全部外置到环境变量，源码与文档不再包含任何真实 Key；旧密钥已失效，请勿继续使用。

## 项目结构

```
NovelWorkshop/
├── backend/                      # FastAPI 后端 (~4400 行 Python)
│   ├── main.py                  # 入口 + 启动配置
│   ├── config/
│   │   ├── .env                 # API Key 配置（已预填）
│   │   ├── settings.py          # 配置加载
│   │   └── model_config.json    # 模型分级路由
│   ├── app/
│   │   ├── agents/              # 8 个 Agent（base + 7 专用）
│   │   │   ├── base_agent.py    # Agent 基类
│   │   │   ├── worldbuilder.py  # 世界观架构师
│   │   │   ├── char_designer.py # 角色设计师（14字段结构化输出）
│   │   │   ├── plot_architect.py # 情节架构师
│   │   │   ├── chapter_writer.py # 章节写手
│   │   │   ├── consistency_checker.py # 一致性审查员
│   │   │   ├── timeline_keeper.py # 时间线管理员
│   │   │   ├── humanizer_agent.py # 文风润色师
│   │   │   └── main_agent.py    # 总调度 Agent
│   │   ├── api/                 # 34 个 REST API 端点
│   │   │   ├── router.py        # 路由注册
│   │   │   ├── books.py         # 书籍 CRUD + 状态查询
│   │   │   ├── chapters.py      # 章节 CRUD + 导出（含 PUT 更新）
│   │   │   ├── workflows.py     # 工作流启动/状态/列表
│   │   │   ├── approvals.py     # 审批获取/提交（通过/驳回/修改）
│   │   │   ├── characters.py    # 角色管理
│   │   │   ├── world.py         # 世界观管理
│   │   │   ├── outline.py       # 大纲管理
│   │   │   ├── hooks.py         # 伏笔管理
│   │   │   ├── timeline.py      # 时间线管理
│   │   │   └── agents.py        # Agent 列表/模型配置
│   │   ├── llm/                 # 双 Provider LLM 客户端
│   │   │   ├── client.py        # LLM 统一接口
│   │   │   ├── volcano.py       # 火山引擎适配
│   │   │   ├── deepseek.py      # DeepSeek 适配
│   │   │   └── router.py        # 模型分级路由（自动选最优）
│   │   ├── models/              # Pydantic 数据模型
│   │   ├── prompts/             # 8 个 Agent 的 System Prompt
│   │   ├── tools/               # 工具脚本
│   │   │   ├── finalize_chapter.py  # 章节定稿 + LLM 摘要生成
│   │   │   ├── split_character_profile.py # 角色14字段拆分
│   │   │   ├── compose_context.py   # 上下文组装
│   │   │   ├── apply_state.py       # 状态应用
│   │   │   ├── file_ops.py          # 文件操作
│   │   │   └── style_analyzer.py    # 风格分析
│   │   └── workflows/           # 4 条工作流引擎
│   │       ├── engine.py        # 核心引擎（审批暂停/恢复/持久化）
│   │       ├── novel_setup.py   # 新书设定流程
│   │       ├── chapter_production.py # 章节生产流程
│   │       ├── revision.py      # 修订润色流程
│   │       └── character_import.py # 角色导入流程
│   └── data/workspaces/         # 运行时书籍工作区（自动创建）
├── frontend/                     # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── pages/               # 5 个核心页面
│   │   │   ├── Dashboard.tsx    # 仪表盘（书籍列表）
│   │   │   ├── Writing.tsx      # 写作工作台
│   │   │   ├── Characters.tsx   # 角色管理
│   │   │   ├── WorldBuilding.tsx # 世界观设定
│   │   │   └── Outline.tsx      # 大纲编辑
│   │   ├── components/          # 12 个组件
│   │   │   ├── Layout.tsx       # 整体布局
│   │   │   ├── Sidebar.tsx      # 侧边导航
│   │   │   ├── BookCard.tsx     # 书籍卡片
│   │   │   ├── WorkflowStatus.tsx  # 工作流状态面板
│   │   │   ├── WorkflowProgress.tsx # 进度条
│   │   │   ├── ApprovalPanel.tsx   # 审批面板（通过/驳回/修改）
│   │   │   ├── ChapterNode.tsx     # 章节节点
│   │   │   ├── CharacterCard.tsx   # 角色卡片
│   │   │   ├── HookKanban.tsx      # 伏笔看板
│   │   │   ├── RelationGraph.tsx   # 关系图谱
│   │   │   └── TimelineView.tsx    # 时间线视图
│   │   ├── api/client.ts        # API 客户端（34 个端点对接）
│   │   ├── store/index.ts       # Zustand 全局状态
│   │   ├── types/index.ts       # TypeScript 类型定义
│   │   └── data/mock.ts         # Mock 数据（API 失败时降级）
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── postcss.config.js
├── demo.html                     # 独立演示版（浏览器直接打开）
├── start.bat                     # Windows 一键启动脚本
└── README.md                     # 本文件
```

## 完整 API 端点表（34 个）

### 书籍管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/books` | 书籍列表 |
| POST | `/api/books` | 创建书籍 |
| GET | `/api/books/{id}` | 书籍详情 |
| GET | `/api/books/{id}/config` | 写作配置 |
| PUT | `/api/books/{id}/config` | 更新配置 |
| GET | `/api/books/{id}/state/characters` | 角色状态 |
| GET | `/api/books/{id}/state/hooks` | 伏笔状态 |
| GET | `/api/books/{id}/state/timeline` | 时间线状态 |

### 章节管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/books/{id}/chapters` | 章节列表 |
| GET | `/api/books/{id}/chapters/{cid}` | 章节详情 |
| PUT | `/api/books/{id}/chapters/{cid}` | 更新章节（内容/标题/状态） |
| GET | `/api/books/{id}/chapters/{cid}/export` | 导出章节 |

### 工作流
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/books/{id}/workflow/novel-setup` | 启动新书流程 |
| POST | `/api/books/{id}/workflow/chapter-production` | 启动章节生产 |
| POST | `/api/books/{id}/workflow/revision` | 启动修订润色 |
| GET | `/api/workflows/{wid}/status` | 工作流状态 |
| GET | `/api/workflows/list` | 所有工作流列表 |

### 审批
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/workflows/{wid}/approval` | 获取待审批内容 |
| POST | `/api/workflows/{wid}/approval` | 提交审批结果 |

### 世界观 / 角色 / 大纲 / 伏笔 / 时间线
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/PUT | `/api/books/{id}/world` | 世界观 CRUD |
| GET/POST | `/api/books/{id}/characters` | 角色列表/创建 |
| GET/PUT | `/api/books/{id}/characters/{cid}` | 角色详情/更新 |
| GET/PUT | `/api/books/{id}/outline` | 大纲 CRUD |
| GET/POST | `/api/books/{id}/hooks` | 伏笔列表/创建 |
| PUT | `/api/books/{id}/hooks/{hid}` | 更新伏笔 |
| GET/POST | `/api/books/{id}/timeline` | 时间线列表/创建 |

### 系统
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agents` | Agent 列表 |
| GET | `/api/agents/model-config` | 模型分级配置 |

## 模型分级路由

| 任务类型 | Agent | 首选模型 | 降级链 |
|---------|-------|---------|--------|
| creative_high | worldbuilder, char_designer | 🔥 豆包-pro | DeepSeek → 豆包 |
| reasoning | plot_architect, consistency_checker | 🔥 豆包-pro | DeepSeek → 豆包 |
| creative_bulk | chapter_writer, humanizer | DeepSeek | 豆包 → DeepSeek |
| light | timeline_keeper | DeepSeek | 豆包 → DeepSeek |

## 核心设计理念：对话驱动的分阶段协作

**v3.0 核心变革：** 从"按钮触发工作流"转变为"多轮对话驱动创作"。

用户不应通过点击按钮来启动工作流，而应通过与AI的多轮对话逐步推进创作：

### 对话式创作流程

```
世界观讨论 → 角色设计 → 大纲规划 → 章节摘要 → 正文撰写
   ↓              ↓          ↓           ↓          ↓
 多轮对话      多轮对话    多轮对话     逐章确认    逐章撰写
 确认世界观   确认角色    确认大纲     确认摘要    确认正文
   ↓              ↓          ↓           ↓          ↓
 保存到         保存到      保存到       保存到      保存到
 world.json    chars.json  outline.json chapters.json 章节文件
```

**每个阶段都遵循相同的交互模式：**
1. 用户在对话面板中与AI讨论
2. AI根据讨论结果提出建议/方案
3. 用户反馈修改意见，AI迭代
4. 用户满意后点击"确认"进入下一阶段
5. 已确认的数据保存为结构化文件，并注入后续阶段的AI上下文

### 风格统一机制

所有对话和写作共享一套结构化 style_guide，确保从世界观到正文的全流程风格一致：

```json
{
  "style_guide": {
    "narrative_pov": "第三人称限知视角",
    "tone": "轻松幽默但关键时刻严肃",
    "dialogue_style": "简洁有力，角色语言要有辨识度",
    "chapter_ending_hook": true,
    "chapter_ending_hook_instruction": "每章结尾必须设置悬念钩子或情感锚点",
    "pacing": {
      "overall_curve": "慢热开局，逐步加速，每10章一个小高潮，每30章一个大高潮",
      "tension_density": "每2000字至少一个冲突点或爽点",
      "climax_frequency": "每5章一个转折，每15章一个大高潮"
    },
    "webnovel_conventions": {
      "face_slapping_rhythm": "压抑3章，爆发1章",
      "power_progression": "每10章一个小境界突破",
      "foreshadowing_rules": "伏笔最多跨5章必须回收，重要伏笔跨卷回收"
    },
    "custom_rules": "用户自由填写的额外规则"
  }
}
```

**style_guide 注入机制：**
- 每个阶段的 system prompt 都包含 style_guide 内容
- 对话上下文中携带已确认的前序阶段成果（大纲、角色、世界观）
- 确保后续写作时AI始终遵循统一的风格规范

## 新增：通用对话 API（v3.0）

### 对话端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/books/{id}/chat` | 发送对话消息（通用，通过context区分场景） |
| GET | `/api/books/{id}/chat/history` | 获取对话历史 |
| POST | `/api/books/{id}/chat/confirm-stage` | 确认当前阶段，推进到下一阶段 |

### 对话 API 请求/响应格式

**POST /api/books/{id}/chat**
```json
// 请求
{
  "context": "worldbuilding | character | outline | writing",
  "message": "用户消息文本",
  "context_id": "可选，角色ID或章节ID"
}

// 响应
{
  "reply": "AI回复内容（Markdown格式）",
  "stage": "当前阶段",
  "stage_data": {},
  "suggestions": ["建议操作1", "建议操作2"]
}
```

### 对话状态存储

每个场景的对话历史独立存储：
```
{book_dir}/runtime/chat_{context}.json
```

结构：
```json
{
  "context": "worldbuilding|character|outline|writing",
  "context_id": "可选的角色ID或章节ID",
  "stage": "当前阶段名称",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "...", "stage": "..."},
    {"role": "assistant", "content": "...", "timestamp": "...", "stage": "..."}
  ],
  "stage_data": {}
}
```

### 各场景 System Prompt 要点

| context | AI 角色 | 核心职责 |
|---------|---------|---------|
| worldbuilding | 资深世界观架构师 | 引导用户构建地理、势力、力量体系、历史、社会规则 |
| character | 专业角色设计师 | 引导用户设计角色的14个字段，确保角色立体丰满 |
| outline | 资深剧情策划 | 基于世界观和角色，引导用户规划大纲和剧情走向 |
| writing | 专业网文写手 | 基于已确认的设定撰写正文，遵循 style_guide 所有规范 |

### 阶段确认与推进

当用户点击"确认"按钮时：
1. 前端调用 `confirm-stage` API
2. 后端将当前 stage_data 中的成果保存到对应文件（world.json/outline.json等）
3. 切换到下一阶段，新阶段的 system prompt 自动注入已确认的前序成果
4. AI发送一条欢迎消息，引导用户进入新阶段的讨论

### 前端改造：通用 ChatPanel 组件

创建可复用的 `ChatPanel.tsx` 组件：
```typescript
interface ChatPanelProps {
  bookId: string
  context: 'worldbuilding' | 'character' | 'outline' | 'writing'
  contextId?: string  // 角色/章节的ID
  onStageDataUpdate?: (data: any) => void
}
```

包含：
- 消息列表（用户靠右，AI靠左，Markdown渲染）
- 输入框 + 发送按钮（Enter发送，Shift+Enter换行）
- 快捷建议按钮（suggestions）
- 加载状态动画
- 自动滚动到最新消息

### 各页面改造方案

每个页面统一采用三栏布局：
- **左侧**：导航（章节列表/角色列表/世界观分类/大纲树）
- **中间**：ChatPanel 对话面板
- **右侧**：当前阶段数据展示 + 确认按钮

| 页面 | 左侧 | 中间 | 右侧 |
|------|------|------|------|
| WorldBuilding.tsx | 世界观分类导航 | ChatPanel context="worldbuilding" | 当前设定 + 确认按钮 |
| Characters.tsx | 角色列表 | ChatPanel context="character" | 角色14字段 + 确认按钮 |
| Outline.tsx | 卷/章节树 | ChatPanel context="outline" | 大纲结构 + 确认按钮 |
| Writing.tsx | 章节列表 | ChatPanel context="writing" | 风格规范 + 章节数据 |

## v3.2 更新内容（本轮迭代）
- ✅ 修复空 JSON 文件导致后端 500 崩溃的问题：`read_json` 增加空文件/损坏文件自动修复（备份+重置）
- ✅ `ensure_workspace_structure` 增强：检测并重新初始化已存在但为空的 JSON 文件
- ✅ `apply_state.py` 全面改用 `read_json`，消除所有直接 `json.loads` 的崩溃隐患
- ✅ start.bat 增强：端口清理 + 后端健康检查 + 启动失败提示

## v3.1 更新内容
- ✅ 数据管线公共模块 `app/utils/data_pipeline.py`：抽取 `generate_chapters_from_outline` 和 `save_chapter_summary`，消除 chat.py/outline.py 重复代码
- ✅ 大纲→分章自动联动：对话提取大纲或 PUT 更新大纲后，自动生成 chapters.json 章节条目
- ✅ 写作前章摘要注入：writing context 的 system prompt 自动注入前一章摘要，实现章节衔接
- ✅ 写作正文持久化：对话产出的正文自动保存到 `chapters/final/chapter-XXX.md`，同步更新 chapters.json 状态/字数
- ✅ 全页面数据联动：ChatPanel 新增 `onDataUpdate` 回调，世界观/角色/大纲/写作页面的对话结果自动回写结构化数据
- ✅ Dashboard 去 mock：伏笔和章节数据改为从 store 读取真实 API 数据
- ✅ 世界观布局优化：势力关系图改为可折叠（默认收起），tab 区域改为弹性布局
- ✅ Writing 页面 LeftPanel 改造：显示真实章节进度、写作素材就绪指示器、动态对话提示

## v3.0 更新内容
- ✅ start.bat 修复：`cd /d "%~dp0"` 解决双击闪退 + 纯英文 + 独立窗口
- ✅ settings.py 修复：添加 `volcano_pro_endpoint` + `extra = "ignore"` 防止 pydantic 拒绝未知字段
- ✅ 后端：通用对话API（chat.py），支持4个场景的对话式交互
- ✅ 前端：ChatPanel 通用组件 + 4个页面全部改为对话驱动
- ✅ style_guide 结构化为完整写作规范体系（文风/钩子/节奏/网文惯例）
- ✅ 风格统一机制：style_guide 注入每个阶段的 system prompt

## v1.2 更新内容（上轮迭代）
- ✅ startWorkflow 返回值对齐
- ✅ 新增 PUT chapters 端点
- ✅ 章节摘要 LLM 自动生成
- ✅ chapters GET 字段补全
- ✅ 前端 WorkflowStatus / ApprovalPanel / API client / store 对齐
- ✅ 审批流程真实化 + 工作流状态持久化
- ✅ 角色 14 字段结构化输出

## 版本迭代约定
- 每次修改都更新本 PRD，迭代版本号（v3.0 → v3.1 → ...）
- 下次会话先读 PRD 恢复上下文，基于最新版本做修改
- 🔄 = 进行中 | ✅ = 已完成 | ❌ = 已取消 | 📋 = 待做

## 代码质量原则：闭环与整体性
- **每个功能必须端到端闭环**：前端按钮 → API调用 → 后端处理 → 数据持久化 → 前端展示，缺一不可
- **不留死代码**：如果某个功能被新方案取代（如按钮式工作流被对话式取代），旧代码要删除或标注废弃
- **不做半成品**：每个文件、每个函数都要有明确的调用方和被调用方，不能有孤立模块
- **验收标准**：运行项目时，每个页面、每个按钮都要能用，不能有"点击无响应"的情况
- **架构清晰**：前端组件之间、后端模块之间的调用关系要明确，不能出现循环依赖或冗余层
