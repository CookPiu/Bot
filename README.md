# 飞书智能任务管理系统

一个基于飞书多维表格的智能任务管理系统，实现了自动化任务分配、进度跟踪和质量评估功能。系统采用现代化的微服务架构，集成了多种AI大语言模型和飞书生态。

## 📋 项目概述

这是一个企业级的智能任务管理解决方案，通过飞书机器人提供直观的用户交互体验，使用多维表格作为数据存储后端，并集成了多种AI模型来实现智能化的任务分配和质量评估。

## 🚀 核心特性

- **智能任务分配**：基于技能匹配和LLM评估的自动候选人推荐
- **多维表格集成**：使用飞书多维表格作为数据存储和管理后端
- **实时消息交互**：通过飞书机器人进行任务通知和状态更新
- **自动化质量控制**：集成CI/CD流程，自动代码审查和评分
- **可视化报告**：每日任务统计和绩效分析
- **多LLM支持**：支持DeepSeek、OpenAI、Google Gemini等多种大语言模型
- **GitHub集成**：自动监控代码提交和CI/CD状态
- **Docker化部署**：完整的容器化解决方案，支持一键部署

## 🏗️ 技术架构

### 核心技术栈
- **后端框架**: FastAPI (Python 3.9+)
- **数据存储**: 飞书多维表格 (Bitable)
- **消息平台**: 飞书开放平台 API
- **AI集成**: DeepSeek、OpenAI、Google Gemini
- **容器化**: Docker + Docker Compose
- **版本控制**: GitHub Webhooks集成

### 系统架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   飞书机器人     │◄──►│  FastAPI 服务器  │◄──►│   外部 APIs     │
│                 │    │                 │    │                 │
│ • 消息接收      │    │ • 业务逻辑      │    │ • LLM APIs      │
│ • 卡片交互      │    │ • 任务管理      │    │ • GitHub API    │
│ • 通知推送      │    │ • 数据处理      │    │ • Bitable API   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 项目结构

### 根目录文件
```
├── main.py                    # 应用入口文件
├── requirements.txt           # Python依赖包
├── docker-compose.yml         # Docker编排配置
├── Dockerfile                 # Docker镜像构建
├── .env / .env.example       # 环境变量配置
├── README.md                 # 项目文档
├── README_DEPLOYMENT.md      # 部署文档
├── deploy.py                 # 部署脚本
├── monitor.py                # 监控脚本
└── app.log                   # 应用日志
```

### 核心应用模块 (`app/`)
```
app/
├── __init__.py               # 包初始化
├── config.py                 # 配置管理
├── api.py                    # REST API路由
├── webhooks.py               # Webhook处理器
├── bitable.py                # 飞书多维表格客户端
├── services/                 # 业务服务层
│   ├── task_manager.py       # 任务管理核心
│   ├── feishu.py            # 飞书服务集成
│   ├── llm.py               # LLM服务抽象
│   ├── ci.py                # CI/CD集成
│   └── match.py             # 智能匹配算法
├── api/                     # API模块
└── utils/                   # 工具函数
```

### 前端模块 (`${Bot}/`)
```
${Bot}/
├── package.json             # Node.js依赖
├── tsconfig.json           # TypeScript配置
├── src/                    # 源代码
├── public/                 # 静态资源
├── dist/                   # 构建输出
└── config/                 # 配置文件
```

## 🔧 核心功能模块

### 1. 任务管理系统 (`task_manager.py`)
- **任务状态管理**: 支持8种任务状态流转
- **智能分配**: 基于技能匹配的自动候选人推荐
- **进度跟踪**: 实时任务状态更新和通知
- **质量控制**: 集成AI评分和人工审核

### 2. 飞书集成服务 (`feishu.py`)
- **消息推送**: 支持文本、卡片、富文本消息
- **长连接**: WebSocket实时消息接收
- **用户管理**: 用户信息获取和权限验证
- **群组管理**: 群聊消息处理和通知

### 3. 多维表格客户端 (`bitable.py`)
- **数据CRUD**: 完整的增删改查操作
- **表格管理**: 多表关联和数据同步
- **字段映射**: 灵活的数据结构适配
- **批量操作**: 高效的批量数据处理

### 4. LLM服务抽象 (`llm.py`)
- **多模型支持**: DeepSeek、OpenAI、Gemini
- **统一接口**: 抽象化的LLM调用接口
- **错误处理**: 完善的重试和降级机制
- **性能优化**: 异步调用和超时控制

### 5. Webhook处理器 (`webhooks.py`)
- **事件路由**: 智能的消息和事件分发
- **命令解析**: 支持多种命令格式和参数
- **安全验证**: 签名验证和权限控制
- **异步处理**: 高并发的事件处理能力

## 📦 快速开始

### 环境要求
- Python 3.9+
- 飞书企业账号
- 多维表格应用权限
- Docker (可选，用于容器化部署)

### 本地开发

1. **克隆项目**
```bash
git clone <repository-url>
cd Bot
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

### Docker部署

1. **使用Docker Compose一键部署**
```bash
docker-compose up -d
```

2. **查看服务状态**
```bash
docker-compose ps
docker-compose logs -f
```

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

## 🚀 部署和运维

### Docker化部署
- **多服务编排**: 应用服务 + Nginx + Redis
- **健康检查**: 自动故障检测和恢复
- **日志管理**: 统一的日志收集和轮转
- **环境隔离**: 开发、测试、生产环境分离

### 监控和维护
- **性能监控**: 系统资源和API响应时间
- **错误追踪**: 详细的错误日志和堆栈信息
- **自动重启**: 服务异常时的自动恢复机制
- **数据备份**: 定期的配置和数据备份

## 💡 系统特色

1. **智能化**: 集成多种AI模型，实现智能任务分配和质量评估
2. **自动化**: 完整的CI/CD流程，从任务创建到验收全自动化
3. **可扩展**: 模块化设计，易于扩展新功能和集成新服务
4. **高可用**: Docker化部署，支持负载均衡和故障恢复
5. **用户友好**: 基于飞书生态，提供直观的交互体验

## 📚 相关文档

- [部署指南](README_DEPLOYMENT.md) - 详细的部署配置说明
- [API文档](http://localhost:8000/docs) - FastAPI自动生成的API文档
- [飞书开放平台](https://open.feishu.cn/) - 飞书应用开发文档

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目。在贡献代码前，请确保：

1. 代码符合项目的编码规范
2. 添加必要的测试用例
3. 更新相关文档
4. 通过所有CI检查

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

这个项目展现了现代化企业级应用的最佳实践，结合了AI技术、微服务架构和DevOps理念，为团队协作和任务管理提供了完整的解决方案。

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