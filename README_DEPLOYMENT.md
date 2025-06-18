# Feishu Chat-Ops 多维表格部署指南

## 项目概述

本项目是一个基于飞书多维表格的任务管理系统，实现了自动化的任务分配、进度跟踪和质量评估功能。系统通过飞书机器人与用户交互，使用多维表格存储任务和人员信息，并集成了GitHub CI/CD流程。

## 核心功能

### 1. 多维表格集成
- **任务表格**：存储任务信息、状态、分配情况
- **人员表格**：管理候选人信息、技能标签、绩效数据
- **自动化操作**：创建、更新、查询表格记录

### 2. 智能任务分配
- 基于技能匹配的候选人推荐
- LLM驱动的智能评分系统
- 自动发送任务邀请通知

### 3. 质量管控
- 自动化代码审查
- CI/CD状态监控
- 智能评分和反馈

### 4. 飞书集成
- 消息推送和交互
- 卡片式任务操作界面
- 命令行式任务管理

## 部署步骤

### 1. 环境准备

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

### 2. 飞书应用配置

#### 2.1 创建飞书应用
1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret

#### 2.2 配置应用权限
在应用管理页面添加以下权限：
- `im:message` - 发送消息
- `im:message.group_at_msg` - 群组@消息
- `im:message.p2p_msg` - 私聊消息
- `bitable:app` - 多维表格应用权限
- `contact:user.id` - 获取用户ID

#### 2.3 配置事件订阅
1. 在「事件订阅」页面配置回调地址：`https://your-domain.com/webhook/feishu`
2. 订阅以下事件：
   - `im.message.receive_v1` - 接收消息
   - `application.bot.menu_v6` - 机器人菜单

### 3. 多维表格设置

#### 3.1 创建多维表格应用
1. 在飞书中创建多维表格
2. 创建两个数据表：

**任务表 (Task Table)**
```
字段名称          字段类型        说明
task_id          单行文本        任务唯一标识
title            单行文本        任务标题
description      多行文本        任务描述
status           单选           状态(pending/assigned/in_progress/submitted/reviewing/completed/rejected)
skill_tags       多选           技能标签
deadline         日期           截止时间
urgency          单选           紧急程度(low/normal/high/urgent)
assignee         单行文本        负责人用户ID
created_by       单行文本        创建者用户ID
created_at       日期时间        创建时间
accepted_at      日期时间        接受时间
submitted_at     日期时间        提交时间
completed_at     日期时间        完成时间
submission_url   单行文本        提交链接
submission_note  多行文本        提交说明
final_score      数字           最终评分
reward_points    数字           奖励积分
acceptance_criteria 多行文本     验收标准
estimated_hours  数字           预估工时
```

**人员表 (Person Table)**
```
字段名称              字段类型        说明
user_id              单行文本        用户唯一标识
name                 单行文本        姓名
skill_tags           多选           技能标签
performance_score    数字           绩效评分
completed_tasks      数字           完成任务数
total_score          数字           总评分
reward_points        数字           总积分
hours_available      数字           可用工时/周
last_active          日期时间        最后活跃时间
availability         复选框          是否可用
```

#### 3.2 获取表格信息
1. 获取多维表格的 App Token
2. 获取任务表和人员表的 Table ID

### 4. 环境变量配置

创建 `.env` 文件：

```env
# 飞书配置
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxx
FEISHU_ENCRYPT_KEY=xxxxxxxxxx

# 多维表格配置
FEISHU_BITABLE_APP_TOKEN=xxxxxxxxxx
FEISHU_TASK_TABLE_ID=xxxxxxxxxx
FEISHU_PERSON_TABLE_ID=xxxxxxxxxx

# LLM配置 (选择一个)
# DeepSeek
DEEPSEEK_API_KEY=sk-xxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1

# GitHub配置 (可选)
GITHUB_WEBHOOK_SECRET=xxxxxxxxxx

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_RELOAD=false

# 系统配置
MAX_RETRY_ATTEMPTS=3
MIN_PASS_SCORE=70
LLM_TIMEOUT=30
LOG_LEVEL=INFO
```

### 5. 启动服务

#### 5.1 开发环境
```bash
# 直接启动
python main.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5.2 生产环境
```bash
# 使用Docker
docker build -t feishu-chatops .
docker run -d -p 8000:8000 --env-file .env feishu-chatops

# 或使用docker-compose
docker-compose up -d
```

### 6. 配置反向代理

使用Nginx配置HTTPS和域名：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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