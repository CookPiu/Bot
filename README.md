# Feishu Chat-Ops MVP

一个基于飞书多维表格的智能任务管理系统，实现自动化任务分配、进度跟踪和质量评估。

## 🚀 核心特性

- **智能任务分配**：基于技能匹配和LLM评估的自动候选人推荐
- **多维表格集成**：使用飞书多维表格作为数据存储和管理后端
- **实时消息交互**：通过飞书机器人进行任务通知和状态更新
- **自动化质量控制**：集成CI/CD流程，自动代码审查和评分
- **可视化报告**：每日任务统计和绩效分析
- **多LLM支持**：支持OpenAI、DeepSeek等多种大语言模型
- **GitHub集成**：自动监控代码提交和CI/CD状态

## 🏗️ 技术架构

### 后端技术栈
- **框架**: FastAPI (Python)
- **数据存储**: Feishu Bitable
- **LLM集成**: DeepSeek-R1, Google Gemini, OpenAI
- **消息平台**: Feishu Open API
- **版本控制**: GitHub Webhooks

### 系统架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Feishu Bot    │    │  FastAPI Server │    │  External APIs  │
│                 │◄──►│                 │◄──►│                 │
│ • 消息接收      │    │ • 业务逻辑      │    │ • LLM APIs      │
│ • 卡片交互      │    │ • 任务管理      │    │ • GitHub API    │
│ • 通知推送      │    │ • 数据处理      │    │ • Bitable API   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 快速开始

### 环境要求
- Python 3.8+
- 飞书企业账号
- 多维表格应用权限

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd Bot
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的API密钥
```

4. **启动服务**
```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 环境变量配置

创建 `.env` 文件并配置以下变量：

```env
# Feishu配置
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
FEISHU_VERIFICATION_TOKEN=your_verification_token
FEISHU_ENCRYPT_KEY=your_encrypt_key

# LLM配置
DEEPSEEK_API_KEY=your_deepseek_key
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
DEFAULT_LLM_MODEL=deepseek

# Bitable配置
BITABLE_APP_TOKEN=your_bitable_app_token
TASK_TABLE_ID=your_task_table_id
CANDIDATE_TABLE_ID=your_candidate_table_id

# GitHub配置（可选）
GITHUB_WEBHOOK_SECRET=your_github_secret

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

## 🔧 API文档

启动服务后，访问以下地址查看API文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 主要API端点

#### 任务管理
- `POST /api/v1/tasks` - 创建任务
- `GET /api/v1/tasks/{task_id}` - 获取任务详情
- `POST /api/v1/tasks/{task_id}/accept` - 接受任务
- `POST /api/v1/tasks/{task_id}/submit` - 提交任务

#### 候选人管理
- `GET /api/v1/candidates` - 获取候选人列表
- `GET /api/v1/candidates/{user_id}` - 获取候选人详情

#### 统计报告
- `GET /api/v1/reports/daily` - 每日报告
- `GET /api/v1/stats/overview` - 统计概览

#### Webhook
- `POST /webhooks/feishu` - Feishu事件回调
- `POST /webhooks/github` - GitHub事件回调

## 🤖 使用指南

### 飞书机器人命令

在飞书中与机器人对话，支持以下命令：

```
/help                    # 显示帮助信息
/task list              # 查看我的任务列表
/task status <任务ID>    # 查看任务状态
/status                 # 查看个人统计
```

### 工作流程

1. **任务创建**：管理员通过API或界面创建任务
2. **自动分配**：系统根据技能匹配推荐候选人
3. **任务接受**：候选人通过飞书消息接受任务
4. **进度跟踪**：系统监控任务进度和状态变化
5. **质量评估**：提交后自动进行质量检查和评分
6. **完成确认**：通过评估后自动完成任务并发放奖励

### 交互卡片
机器人支持丰富的卡片交互：
- 任务接受/拒绝按钮
- 任务详情展示
- 进度状态更新
- 质量评估结果

## 📊 数据模型

### 任务表 (Tasks)
| 字段 | 类型 | 描述 |
|------|------|------|
| task_id | String | 任务ID |
| title | String | 任务标题 |
| description | Text | 任务描述 |
| skill_tags | Array | 技能标签 |
| status | String | 任务状态 |
| assignee | String | 负责人 |
| deadline | DateTime | 截止时间 |
| created_at | DateTime | 创建时间 |

### 候选人表 (Candidates)
| 字段 | 类型 | 描述 |
|------|------|------|
| user_id | String | 用户ID |
| name | String | 姓名 |
| skill_tags | Array | 技能标签 |
| performance | Float | 历史表现 |
| hours_available | Integer | 可用工时 |
| last_active | DateTime | 最后活跃时间 |

## 🔒 安全考虑

### 数据隐私
- LLM调用时对候选人数据进行匿名化处理
- 敏感信息不传输给第三方服务
- 支持数据加密和访问控制

### API安全
- Webhook签名验证
- API密钥管理
- 请求频率限制
- HTTPS强制加密

## 🧪 测试

### 运行测试
```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_task_manager.py

# 生成覆盖率报告
pytest --cov=app tests/
```

### 测试结构
```
tests/
├── test_api.py              # API接口测试
├── test_task_manager.py     # 任务管理测试
├── test_llm_service.py      # LLM服务测试
├── test_webhooks.py         # Webhook测试
└── conftest.py              # 测试配置
```

## 📈 监控和日志

### 日志配置
- 应用日志: `app.log`
- 错误级别: INFO及以上
- 日志轮转: 按日期自动轮转

### 健康检查
- 端点: `GET /health`
- 监控各服务状态
- 支持外部监控系统集成

## 🚀 部署指南

### 详细部署文档

完整的部署指南请参考：[**部署文档 (README_DEPLOYMENT.md)**](README_DEPLOYMENT.md)

该文档包含：
- 飞书应用配置步骤
- 多维表格设置指南
- 环境变量详细说明
- Docker 和生产环境部署
- 故障排除和维护指南

### 快速部署

```bash
# Docker 部署
docker build -t feishu-chatops .
docker run -d -p 8000:8000 --env-file .env feishu-chatops

# 或使用 docker-compose
docker-compose up -d
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如有问题或建议，请：
1. 查看 [FAQ](docs/FAQ.md)
2. 提交 [Issue](../../issues)
3. 联系开发团队

## 🗺️ 路线图

### v1.1 计划功能
- [ ] 任务模板系统
- [ ] 高级统计分析
- [ ] 移动端适配
- [ ] 多语言支持

### v2.0 计划功能
- [ ] 工作流可视化编辑器
- [ ] 智能推荐系统
- [ ] 集成更多第三方平台
- [ ] 企业级权限管理

---

**Feishu Chat-Ops** - 让任务管理更智能，让协作更高效！ 🎉