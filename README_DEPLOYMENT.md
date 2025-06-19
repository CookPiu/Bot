# Feishu Chat-Ops 多维表格部署指南

## 飞书智能任务管理系统 - 部署指南

## 📋 项目概述

本项目是一个基于飞书多维表格的智能任务管理系统，实现了自动化的任务分配、进度跟踪和质量评估功能。系统采用现代化的微服务架构，通过飞书机器人与用户交互，使用多维表格存储任务和人员信息，并集成了多种AI模型和GitHub CI/CD流程。

## 🏗️ 系统架构

### 技术栈
- **后端**: FastAPI (Python 3.9+)
- **数据存储**: 飞书多维表格 (Bitable)
- **AI集成**: DeepSeek、OpenAI、Google Gemini
- **消息平台**: 飞书开放平台 API
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **缓存**: Redis

### 服务组件
- **主应用服务**: FastAPI应用，处理业务逻辑
- **Nginx**: 反向代理和负载均衡
- **Redis**: 缓存和会话管理
- **飞书机器人**: 消息接收和推送
- **Webhook服务**: GitHub集成和事件处理

## 🔧 核心功能

### 1. 智能任务管理
- **任务生命周期**: 8种状态的完整流转管理
- **智能分配**: 基于技能匹配和AI评估的候选人推荐
- **进度跟踪**: 实时状态更新和自动通知
- **质量控制**: 集成CI/CD和AI评分系统

### 2. 飞书生态集成
- **多维表格**: 任务和人员数据的结构化存储
- **机器人交互**: 支持文本命令和卡片交互
- **消息推送**: 实时任务通知和状态更新
- **长连接**: WebSocket实时消息接收

### 3. AI智能化
- **多模型支持**: DeepSeek、OpenAI、Gemini
- **智能评分**: 自动代码质量评估
- **候选人匹配**: 基于技能和历史表现的推荐
- **自然语言处理**: 任务描述和需求分析

### 4. DevOps集成
- **GitHub Webhooks**: 自动监控代码提交
- **CI/CD状态**: 实时构建和部署状态跟踪
- **自动化验收**: 基于CI结果的任务验收
- **质量门禁**: 代码质量和测试覆盖率检查

## 🚀 部署步骤

### 方式一：Docker Compose 部署（推荐）

#### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd Bot

# 确保Docker和Docker Compose已安装
docker --version
docker-compose --version
```

#### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件
vim .env  # 或使用其他编辑器
```

#### 3. 一键部署
```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 4. 验证部署
```bash
# 检查健康状态
curl http://localhost:8000/health

# 访问API文档
open http://localhost:8000/docs
```

### 方式二：本地开发部署

#### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd Bot

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

#### 3. 启动服务
```bash
# 启动主应用
python main.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## ⚙️ 飞书应用配置

### 1. 创建飞书应用
1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret

### 2. 配置应用权限
#### 必需权限：
- `im:message` - 发送消息
- `im:message.group_at_msg` - 接收群聊@消息
- `im:message.group_at_msg:readonly` - 读取群聊@消息
- `im:message.p2p_msg` - 接收私聊消息
- `im:message.p2p_msg:readonly` - 读取私聊消息
- `bitable:app` - 多维表格应用权限
- `contact:user.id:readonly` - 读取用户ID

### 3. 配置事件订阅
#### 事件类型：
- `im.message.receive_v1` - 接收消息事件
- `im.message.message_read_v1` - 消息已读事件
- `application.bot.menu_v6` - 机器人菜单事件

#### 请求地址：
```
https://your-domain.com/webhooks/feishu
```

### 4. 配置机器人
1. 启用机器人功能
2. 设置机器人名称和头像
3. 配置机器人描述和帮助信息
4. 添加到相关群组
5. 配置机器人菜单（可选）

## 📊 多维表格配置

### 1. 创建多维表格应用
1. 在飞书中创建新的多维表格
2. 获取多维表格的 App Token
3. 创建以下两个数据表

### 2. 任务表结构 (Task Table)
| 字段名称 | 字段类型 | 必填 | 说明 |
|---------|---------|------|------|
| task_id | 单行文本 | ✓ | 任务唯一标识 |
| title | 单行文本 | ✓ | 任务标题 |
| description | 多行文本 | ✓ | 任务详细描述 |
| status | 单选 | ✓ | 任务状态 |
| skill_tags | 多选 | ✓ | 所需技能标签 |
| deadline | 日期时间 | ✓ | 截止时间 |
| urgency | 单选 | ✓ | 紧急程度 |
| assignee | 单行文本 | - | 负责人用户ID |
| created_by | 单行文本 | ✓ | 创建者用户ID |
| created_at | 日期时间 | ✓ | 创建时间 |
| accepted_at | 日期时间 | - | 接受时间 |
| submitted_at | 日期时间 | - | 提交时间 |
| completed_at | 日期时间 | - | 完成时间 |
| submission_url | 单行文本 | - | 提交链接 |
| submission_note | 多行文本 | - | 提交说明 |
| final_score | 数字 | - | 最终评分(0-100) |
| reward_points | 数字 | ✓ | 奖励积分 |
| acceptance_criteria | 多行文本 | - | 验收标准 |
| estimated_hours | 数字 | ✓ | 预估工时 |

#### 状态选项配置：
- `pending` - 待分配
- `assigned` - 已分配
- `in_progress` - 进行中
- `submitted` - 已提交
- `reviewing` - 审核中
- `completed` - 已完成
- `rejected` - 已拒绝
- `cancelled` - 已取消

#### 紧急程度选项：
- `low` - 低
- `normal` - 普通
- `high` - 高
- `urgent` - 紧急

### 3. 候选人表结构 (Candidate Table)
| 字段名称 | 字段类型 | 必填 | 说明 |
|---------|---------|------|------|
| user_id | 单行文本 | ✓ | 用户唯一标识 |
| name | 单行文本 | ✓ | 姓名 |
| skill_tags | 多选 | ✓ | 技能标签 |
| performance_score | 数字 | - | 绩效评分(0-100) |
| completed_tasks | 数字 | - | 完成任务数 |
| total_score | 数字 | - | 总评分 |
| reward_points | 数字 | - | 总积分 |
| hours_available | 数字 | ✓ | 可用工时/周 |
| last_active | 日期时间 | - | 最后活跃时间 |
| availability | 复选框 | ✓ | 是否可用 |
| contact_info | 单行文本 | - | 联系方式 |
| department | 单行文本 | - | 部门 |
| level | 单选 | - | 技能等级 |

#### 技能等级选项：
- `junior` - 初级
- `intermediate` - 中级
- `senior` - 高级
- `expert` - 专家

### 4. 获取表格信息
1. 在多维表格中点击右上角「...」→「高级」→「获取App Token」
2. 复制App Token
3. 获取每个表的Table ID（在表格URL中或通过API获取）

## ⚙️ 环境变量配置

### 1. 创建配置文件
在项目根目录创建 `.env` 文件：

```env
# ===========================================
# 飞书应用配置 (必填)
# ===========================================
FEISHU_APP_ID=cli_xxxxxxxxxx              # 飞书应用ID
FEISHU_APP_SECRET=xxxxxxxxxx               # 飞书应用密钥
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxx       # 事件订阅验证Token
FEISHU_ENCRYPT_KEY=xxxxxxxxxx              # 事件订阅加密Key

# ===========================================
# 多维表格配置 (必填)
# ===========================================
BITABLE_APP_TOKEN=xxxxxxxxxx               # 多维表格App Token
TASK_TABLE_ID=xxxxxxxxxx                   # 任务表ID
CANDIDATE_TABLE_ID=xxxxxxxxxx              # 候选人表ID

# ===========================================
# AI模型配置 (必填)
# ===========================================
LLM_BACKEND=deepseek                       # LLM后端类型: deepseek/openai/gemini

# DeepSeek配置
DEEPSEEK_API_KEY=sk-xxxxxxxxxx             # DeepSeek API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com # DeepSeek API地址
DEEPSEEK_MODEL=deepseek-chat                # 使用的模型名称

# OpenAI配置 (可选)
# OPENAI_API_KEY=sk-xxxxxxxxxx
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-3.5-turbo

# Google Gemini配置 (可选)
# GEMINI_API_KEY=xxxxxxxxxx
# GEMINI_MODEL=gemini-pro

# ===========================================
# GitHub集成配置 (可选)
# ===========================================
GITHUB_TOKEN=ghp_xxxxxxxxxx                # GitHub Personal Access Token
GITHUB_WEBHOOK_SECRET=xxxxxxxxxx           # GitHub Webhook密钥
GITHUB_ENABLE_CI=true                       # 是否启用GitHub CI集成

# ===========================================
# 服务器配置
# ===========================================
SERVER_HOST=0.0.0.0                        # 服务器监听地址
SERVER_PORT=8000                            # 服务器端口
DEBUG=false                                 # 调试模式
LOG_LEVEL=INFO                              # 日志级别: DEBUG/INFO/WARNING/ERROR

# ===========================================
# 缓存配置 (可选)
# ===========================================
REDIS_URL=redis://localhost:6379           # Redis连接URL
REDIS_ENABLE=false                          # 是否启用Redis缓存

# ===========================================
# 安全配置
# ===========================================
JWT_SECRET_KEY=your-super-secret-key        # JWT密钥
ALLOWED_HOSTS=localhost,127.0.0.1           # 允许的主机列表
CORS_ORIGINS=*                              # CORS允许的源

# ===========================================
# 业务配置
# ===========================================
TASK_AUTO_ASSIGN=true                       # 是否启用任务自动分配
TASK_DEADLINE_HOURS=72                      # 默认任务截止时间(小时)
SCORE_THRESHOLD=60                          # 任务通过评分阈值
MAX_RETRY_ATTEMPTS=3                        # 最大重试次数
```

### 2. 配置说明

#### 必填配置项
- **飞书配置**: 从飞书开发者后台获取
- **多维表格配置**: 从多维表格应用中获取
- **AI模型配置**: 至少配置一个LLM后端

#### 可选配置项
- **GitHub集成**: 用于CI/CD集成和代码质量检查
- **Redis缓存**: 提升系统性能，推荐生产环境启用
- **安全配置**: 生产环境建议修改默认值

#### 环境特定配置
```bash
# 开发环境
DEBUG=true
LOG_LEVEL=DEBUG
SERVER_HOST=127.0.0.1

# 生产环境
DEBUG=false
LOG_LEVEL=INFO
SERVER_HOST=0.0.0.0
```

## 🚀 部署启动

### 1. 本地开发环境

#### 安装依赖
```bash
# 克隆项目
git clone <repository-url>
cd Bot

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 启动服务
```bash
# 开发模式启动
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Docker 部署

#### 单容器部署
```bash
# 构建镜像
docker build -t feishu-chatops .

# 运行容器
docker run -d \
  --name feishu-chatops \
  -p 8000:8000 \
  --env-file .env \
  feishu-chatops
```

#### Docker Compose 部署（推荐）
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

### 3. 生产环境配置

#### 系统要求
- **CPU**: 2核心以上
- **内存**: 4GB以上
- **存储**: 20GB以上
- **网络**: 稳定的互联网连接
- **操作系统**: Linux (推荐 Ubuntu 20.04+)

#### 性能优化
```bash
# 使用 Gunicorn 启动（生产环境推荐）
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## 🔧 反向代理配置

### Nginx 配置

#### 基础配置
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL 证书配置
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # 代理配置
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 健康检查端点
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
    
    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 负载均衡配置
```nginx
upstream feishu_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    
    # 健康检查
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://feishu_backend;
        # ... 其他配置
    }
}
```

## 使用指南

### 1. 基本命令

在飞书中与机器人对话，支持以下命令：

```
/help                    # 显示帮助信息
/task list              # 查看我的任务列表
/task status <任务ID>    # 查看任务状态
/status                 # 查看个人统计
```

### 2. API接口

系统提供RESTful API接口：

```bash
# 创建任务
POST /api/tasks
{
  "title": "任务标题",
  "description": "任务描述",
  "skill_tags": ["Python", "FastAPI"],
  "deadline": "2024-01-31T23:59:59",
  "created_by": "user_id"
}

# 获取任务状态
GET /api/tasks/{task_id}

# 接受任务
POST /api/tasks/{task_id}/accept
{
  "user_id": "user_id"
}

# 提交任务
POST /api/tasks/{task_id}/submit
{
  "user_id": "user_id",
  "submission_url": "https://github.com/user/repo/pull/123",
  "submission_note": "提交说明"
}

# 获取候选人列表
GET /api/candidates

# 获取每日报告
GET /api/reports/daily
```

### 3. 工作流程

1. **任务创建**：管理员通过API或界面创建任务
2. **自动分配**：系统根据技能匹配推荐候选人
3. **任务接受**：候选人通过飞书消息接受任务
4. **进度跟踪**：系统监控任务进度和状态变化
5. **质量评估**：提交后自动进行质量检查和评分
6. **完成确认**：通过评估后自动完成任务并发放奖励

## 监控和维护

### 1. 日志监控
```bash
# 查看应用日志
tail -f app.log

# 查看错误日志
grep ERROR app.log
```

### 2. 健康检查
```bash
# 检查服务状态
curl http://localhost:8000/api/health

# 检查配置信息
curl http://localhost:8000/api/config
```

### 3. 数据备份
定期备份飞书多维表格数据，可以通过API导出：
```bash
# 导出任务数据
curl http://localhost:8000/api/tasks > tasks_backup.json

# 导出候选人数据
curl http://localhost:8000/api/candidates > candidates_backup.json
```

## 故障排除

### 常见问题

1. **飞书消息发送失败**
   - 检查App ID和App Secret是否正确
   - 确认应用权限配置
   - 验证用户ID格式

2. **多维表格操作失败**
   - 检查App Token和Table ID
   - 确认表格字段配置
   - 验证数据格式

3. **LLM调用失败**
   - 检查API密钥配置
   - 确认网络连接
   - 验证请求格式

4. **GitHub集成问题**
   - 检查Webhook Secret配置
   - 确认回调地址可访问
   - 验证事件类型

### 调试模式

启用调试模式获取详细日志：
```bash
# 设置日志级别
export LOG_LEVEL=DEBUG

# 启动服务
python main.py
```

## 扩展开发

### 1. 添加新的LLM后端

在 `app/services/llm.py` 中实现新的LLM后端：

```python
class CustomLLMBackend(LLMBackend):
    async def generate_response(self, prompt: str, **kwargs) -> str:
        # 实现自定义LLM调用逻辑
        pass
```

### 2. 扩展任务类型

在 `app/services/task_manager.py` 中添加新的任务处理逻辑：

```python
async def handle_custom_task_type(self, task_data: Dict[str, Any]):
    # 实现自定义任务类型处理
    pass
```

### 3. 添加新的通知渠道

在 `app/services/` 目录下创建新的服务模块，实现通知接口。

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 支持

如有问题或建议，请提交 Issue 或联系项目维护者。