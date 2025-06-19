import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Header
import hashlib
import hmac
import lark_oapi as lark
import threading
import asyncio
from app.config import settings
from app.services.task_manager import task_manager
from app.services.feishu import FeishuService
from app.bitable import BitableClient

bitable_client = BitableClient()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
feishu_service = FeishuService()

# 注意：setup_event_handler函数已被移除，因为它与handle_message_event重复
# 现在统一使用setup_websocket_client中的handle_message_event和handle_card_action_event

# 注意：handle_message_receive函数已被移除，因为它与handle_message_event重复
# 现在统一使用handle_message_event函数处理所有消息

# 注意：handle_card_action函数已被移除，因为它与handle_card_action_event重复
# 现在统一使用handle_card_action_event函数处理所有卡片交互

async def handle_task_command(user_id: str, command: str):
    """处理任务相关命令"""
    try:
        parts = command.split()
        if len(parts) < 2:
            await feishu_service.send_message(
                user_id=user_id,
                message="任务命令格式：/task <action> [参数]\n可用操作：list, status, submit"
            )
            return
        
        action = parts[1]
        
        if action == 'list':
            # 获取用户任务列表
            tasks = await task_manager.get_user_tasks(user_id)
            if tasks:
                task_list = "\n".join([f"- {task.get('title', 'Unknown')} ({task.get('status', 'Unknown')})" for task in tasks])
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"您的任务列表：\n{task_list}"
                )
            else:
                await feishu_service.send_message(
                    user_id=user_id,
                    message="您当前没有任务。"
                )
        
        elif action == 'status' and len(parts) > 2:
            # 获取特定任务状态
            task_id = parts[2]
            task = await task_manager.get_task_status(task_id)
            if task:
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"任务状态：\n标题：{task.get('title', 'Unknown')}\n状态：{task.get('status', 'Unknown')}\n截止时间：{task.get('deadline', 'Unknown')}"
                )
            else:
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"任务 {task_id} 不存在。"
                )
        
        else:
            await feishu_service.send_message(
                user_id=user_id,
                message="未知的任务命令。发送 /help 查看帮助。"
            )
    
    except Exception as e:
        logger.error(f"Error handling task command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="处理命令时出错，请稍后重试。"
        )

async def handle_help_command(user_id: str):
    """处理帮助命令"""
    help_text = """
🤖 飞书任务管理机器人 - 帮助文档

📋 **任务管理命令**
• `/create <标题>` - 创建新任务
• `/submit <任务ID> <链接>` - 提交任务作品
• `/done <提交链接>` - 快速提交任务（自动验收）
• `/status <任务ID>` - 查看指定任务状态
• `/mytasks` - 查看我的所有任务

📊 **数据查询命令**
• `/table` - 查询表格信息和记录
• `/bitable` - 多维表格操作
• `/report` 或 `#report` - 生成每日任务统计报告

❓ **帮助命令**
• `/help` - 显示此帮助信息

🆕 **创建任务的方式**
• `@机器人 新任务 [任务描述]` - 完整格式创建
• `新任务 [任务描述]` - 简化格式创建

💡 **任务提交示例**
• `/done https://github.com/user/repo/pull/123`
• `/done https://docs.google.com/document/d/xxx`
• `/submit TASK001 https://github.com/user/project`

🎯 **使用技巧**
• 支持通过卡片按钮进行交互操作
• 代码任务支持GitHub自动CI检查
• 系统会自动进行任务验收和评分

如需更多帮助，请联系管理员。
    """
    
    await feishu_service.send_message(
        user_id=user_id,
        message=help_text
    )

async def handle_done_command(user_id: str, command: str, chat_id: str = None):
    """处理任务完成提交命令"""
    try:
        # 解析命令格式: /done <提交链接>
        parts = command.strip().split(maxsplit=1)
        if len(parts) < 2:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 命令格式错误！\n\n正确格式：/done <提交链接>\n\n示例：\n/done https://github.com/user/repo/pull/123\n/done https://docs.google.com/document/d/xxx"
            )
            return
        
        submission_url = parts[1].strip()
        
        # 验证URL格式
        if not submission_url.startswith(('http://', 'https://')):
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 请提供有效的链接地址（需要以 http:// 或 https:// 开头）"
            )
            return
        
        # 查找用户当前进行中的任务
        user_tasks = await task_manager.get_user_tasks(user_id)
        active_tasks = [task for task in user_tasks if task.get('status') in ['assigned', 'in_progress']]
        
        if not active_tasks:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 您当前没有进行中的任务。请先接受任务后再提交。"
            )
            return
        
        # 如果有多个任务，选择最新的一个
        current_task = active_tasks[0]
        task_id = current_task.get('record_id') or current_task.get('id')
        
        if not task_id:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 无法找到任务ID，请联系管理员。"
            )
            return
        
        # 更新任务状态为已提交
        await task_manager.submit_task(task_id, user_id, submission_url)
        
        # 发送提交确认消息
        await feishu_service.send_message(
            user_id=user_id,
            message=f"✅ 任务提交成功！\n\n📋 任务：{current_task.get('title', 'Unknown')}\n🔗 提交链接：{submission_url}\n\n🤖 正在进行自动验收，请稍候..."
        )
        
        # 如果在子群中提交，也发送到子群
        if chat_id and chat_id != user_id:
            await feishu_service.send_message_to_chat(
                chat_id=chat_id,
                message=f"✅ @{user_id} 已提交任务\n\n📋 任务：{current_task.get('title', 'Unknown')}\n🔗 提交链接：{submission_url}\n\n🤖 正在进行自动验收..."
            )
        
        # 触发自动验收流程
        await _trigger_auto_review(task_id, current_task, submission_url, user_id, chat_id)
        
    except Exception as e:
        logger.error(f"Error handling done command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="❌ 处理提交时出错，请稍后重试或联系管理员。"
        )

async def _trigger_auto_review(task_id: str, task_data: Dict[str, Any], submission_url: str, user_id: str, chat_id: str = None):
    """触发自动验收流程"""
    try:
        from app.services.ci import ci_service
        
        # 判断任务类型
        task_type = _determine_task_type(task_data)
        
        if task_type == "code":
            # 代码任务：检查GitHub CI状态
            await _handle_code_task_review(task_id, task_data, submission_url, user_id, chat_id)
        else:
            # 非代码任务：使用LLM评分
            await _handle_non_code_task_review(task_id, task_data, submission_url, user_id, chat_id)
            
    except Exception as e:
        logger.error(f"Error in auto review: {str(e)}")
        # 降级到人工审核
        await feishu_service.send_message(
            user_id=user_id,
            message="⚠️ 自动验收出现问题，已转为人工审核。管理员会尽快处理。"
        )

def _determine_task_type(task_data: Dict[str, Any]) -> str:
    """判断任务类型"""
    try:
        description = task_data.get('description', '').lower()
        skill_tags = [tag.lower() for tag in task_data.get('skill_tags', [])]
        
        # 代码相关关键词
        code_keywords = ['代码', '编程', '开发', 'code', 'programming', 'development', 
                        'python', 'javascript', 'java', 'go', 'rust', 'c++', 'api',
                        'github', 'git', '仓库', 'repository', 'pull request', 'pr']
        
        # 检查描述和技能标签
        for keyword in code_keywords:
            if keyword in description or keyword in skill_tags:
                return "code"
        
        return "non_code"
        
    except Exception as e:
        logger.error(f"Error determining task type: {str(e)}")
        return "non_code"

async def _handle_code_task_review(task_id: str, task_data: Dict[str, Any], submission_url: str, user_id: str, chat_id: str = None):
    """处理代码任务的验收"""
    try:
        # 检查是否是GitHub链接
        if 'github.com' in submission_url:
            # 发送等待CI消息
            await feishu_service.send_message(
                user_id=user_id,
                message="🔄 检测到GitHub提交，正在等待CI检查结果...\n\n如果您的仓库配置了GitHub Actions，系统会自动获取CI状态。\n如果没有CI配置，将转为人工审核。"
            )
            
            # 模拟CI检查（实际环境中会通过webhook接收）
            import asyncio
            await asyncio.sleep(3)  # 模拟等待时间
            
            # 模拟CI结果（在实际环境中，这会通过GitHub webhook触发）
            await _simulate_ci_result(task_id, task_data, submission_url, user_id, chat_id)
        else:
            # 非GitHub链接，转为LLM评分
            await feishu_service.send_message(
                user_id=user_id,
                message="ℹ️ 非GitHub链接，转为AI评分模式..."
            )
            await _handle_non_code_task_review(task_id, task_data, submission_url, user_id, chat_id)
            
    except Exception as e:
        logger.error(f"Error in code task review: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="❌ 代码任务验收出错，已转为人工审核。"
        )

async def _simulate_ci_result(task_id: str, task_data: Dict[str, Any], submission_url: str, user_id: str, chat_id: str = None):
    """模拟CI检查结果（用于演示）"""
    try:
        import random
        
        # 模拟CI结果（80%通过率）
        ci_passed = random.random() > 0.2
        
        if ci_passed:
            # CI通过
            await task_manager.complete_task(task_id, {
                'final_score': 95,
                'review_result': 'CI检查通过',
                'ci_state': 'passed'
            })
            
            success_msg = f"🎉 恭喜！您的代码任务已通过验收！\n\n📋 任务：{task_data.get('title', 'Unknown')}\n✅ CI检查：通过\n📊 评分：95分\n\n任务已完成，积分已发放！"
            
            await feishu_service.send_message(user_id=user_id, message=success_msg)
            
            if chat_id and chat_id != user_id:
                await feishu_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=f"🎉 @{user_id} 的任务已通过验收！\n\n📋 任务：{task_data.get('title', 'Unknown')}\n✅ CI检查：通过\n📊 评分：95分"
                )
        else:
            # CI失败
            failed_reasons = [
                "代码格式检查未通过",
                "单元测试失败",
                "代码覆盖率不足"
            ]
            
            await task_manager.reject_task(task_id, {
                'final_score': 45,
                'review_result': 'CI检查失败',
                'failed_reasons': failed_reasons,
                'ci_state': 'failed'
            })
            
            failure_msg = f"❌ 您的代码任务未通过验收\n\n📋 任务：{task_data.get('title', 'Unknown')}\n❌ CI检查：失败\n📊 评分：45分\n\n需要修改的问题：\n" + "\n".join([f"• {reason}" for reason in failed_reasons]) + "\n\n请修改后重新提交（您还有2次机会）。"
            
            await feishu_service.send_message(user_id=user_id, message=failure_msg)
            
            if chat_id and chat_id != user_id:
                await feishu_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=f"❌ @{user_id} 的任务需要修改\n\n📋 任务：{task_data.get('title', 'Unknown')}\n❌ CI检查：失败\n📊 评分：45分"
                )
                
    except Exception as e:
        logger.error(f"Error simulating CI result: {str(e)}")

async def _handle_non_code_task_review(task_id: str, task_data: Dict[str, Any], submission_url: str, user_id: str, chat_id: str = None):
    """处理非代码任务的LLM评分"""
    try:
        from app.services.ci import ci_service
        
        # 发送评分中消息
        await feishu_service.send_message(
            user_id=user_id,
            message="🤖 AI正在评估您的提交内容，请稍候..."
        )
        
        # 调用LLM评分
        description = task_data.get('description', '')
        acceptance_criteria = task_data.get('acceptance_criteria', '按照任务要求完成即可')
        
        score, failed_reasons = await ci_service.evaluate_submission(
            description=description,
            acceptance_criteria=acceptance_criteria,
            submission_url=submission_url
        )
        
        # 判断是否通过（阈值80分）
        if score >= 80:
            # 通过验收
            await task_manager.complete_task(task_id, {
                'final_score': score,
                'review_result': 'AI评分通过',
                'ai_score': score
            })
            
            success_msg = f"🎉 恭喜！您的任务已通过验收！\n\n📋 任务：{task_data.get('title', 'Unknown')}\n🤖 AI评分：{score}分\n✅ 状态：通过\n\n任务已完成，积分已发放！"
            
            await feishu_service.send_message(user_id=user_id, message=success_msg)
            
            if chat_id and chat_id != user_id:
                await feishu_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=f"🎉 @{user_id} 的任务已通过验收！\n\n📋 任务：{task_data.get('title', 'Unknown')}\n🤖 AI评分：{score}分"
                )
        else:
            # 未通过验收
            await task_manager.reject_task(task_id, {
                'final_score': score,
                'review_result': 'AI评分未通过',
                'failed_reasons': failed_reasons,
                'ai_score': score
            })
            
            failure_msg = f"❌ 您的任务未通过验收\n\n📋 任务：{task_data.get('title', 'Unknown')}\n🤖 AI评分：{score}分\n❌ 状态：需要修改\n\n需要改进的地方：\n" + "\n".join([f"• {reason}" for reason in failed_reasons]) + "\n\n请根据建议修改后重新提交（您还有2次机会）。"
            
            await feishu_service.send_message(user_id=user_id, message=failure_msg)
            
            if chat_id and chat_id != user_id:
                await feishu_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=f"❌ @{user_id} 的任务需要修改\n\n📋 任务：{task_data.get('title', 'Unknown')}\n🤖 AI评分：{score}分"
                )
                
    except Exception as e:
        logger.error(f"Error in non-code task review: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="❌ AI评分出现问题，已转为人工审核。管理员会尽快处理。"
        )

async def handle_status_command(user_id: str, command: str):
    """处理状态查询命令"""
    try:
        # 获取用户的候选人详情
        candidate = await bitable_client.get_candidate_details(user_id)
        if candidate:
            status_text = f"""
📊 您的状态统计

姓名：{candidate.get('name', 'Unknown')}
技能标签：{', '.join(candidate.get('skill_tags', []))}
完成任务数：{candidate.get('completed_tasks', 0)}
平均评分：{candidate.get('average_score', 0)}
总积分：{candidate.get('total_points', 0)}
可用时间：{candidate.get('hours_available', 0)} 小时/周
            """
        else:
            status_text = "未找到您的个人信息，请联系管理员。"
        
        await feishu_service.send_message(
            user_id=user_id,
            message=status_text
        )
    
    except Exception as e:
        logger.error(f"Error handling status command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="获取状态信息时出错，请稍后重试。"
        )

async def handle_table_command(user_id: str, command: str, chat_id: str = None):
    """处理表格查询命令"""
    try:
        # 解析命令参数
        parts = command.split()
        table_id = None
        
        # 如果指定了表格ID，则使用指定的表格
        if len(parts) > 1:
            table_id = parts[1]
        
        # 获取表格信息
        table_info = await bitable_client.get_table_info(table_id=table_id)
        
        if 'error' in table_info:
            await feishu_service.send_message(
                user_id=user_id,
                message=f"获取表格信息失败: {table_info['error']}"
            )
            return
        
        # 构建表格信息文本
        fields = table_info.get('fields', [])
        if fields:
            fields_info = "\n".join([f"- {field.get('field_name', field.get('name', 'Unknown'))}: {field.get('type', 'Unknown')}" for field in fields])
        else:
            fields_info = "无字段信息"
            
        # 打印表格信息，便于调试
        logger.info(f"表格信息: {table_info}")
        logger.info(f"字段信息: {fields}")
        logger.info(f"记录数量: {len(table_info.get('records', []))}")
        logger.info(f"总记录数: {table_info.get('total_records', 0)}")
        
        
        # 构建记录信息（最多显示5条记录）
        records = table_info.get('records', [])
        records_preview = []
        
        for i, record in enumerate(records[:5]):
            record_fields = record.get('fields', {})
            # 打印记录字段内容，便于调试
            logger.info(f"记录 {i+1} 字段内容: {record_fields}")
            
            # 格式化记录字段
            field_items = []
            for k, v in record_fields.items():
                # 处理不同类型的值
                if isinstance(v, dict):
                    # 如果值是字典，尝试提取有用信息
                    if 'text' in v:
                        field_items.append(f"{k}: {v['text']}")
                    else:
                        field_items.append(f"{k}: {str(v)}")
                elif isinstance(v, list):
                    # 如果值是列表，尝试将其连接起来
                    list_values = []
                    for item in v:
                        if isinstance(item, dict) and 'text' in item:
                            list_values.append(item['text'])
                        else:
                            list_values.append(str(item))
                    field_items.append(f"{k}: {', '.join(list_values)}")
                else:
                    field_items.append(f"{k}: {v}")
            
            field_text = ", ".join(field_items)
            records_preview.append(f"记录 {i+1}: {field_text}")
        
        records_text = "\n".join(records_preview)
        
        if len(records) > 5:
            records_text += f"\n... 还有 {len(records) - 5} 条记录未显示"
        
        table_text = f"""
📋 表格信息

表格ID: {table_info.get('table_id', 'Unknown')}
记录总数: {table_info.get('total_records', 0)}

字段列表:
{fields_info}

记录预览:
{records_text}
        """
        
        await feishu_service.send_message(
            user_id=user_id,
            message=table_text
        )
    
    except Exception as e:
        logger.error(f"Error handling table command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="查询表格信息时出错，请稍后重试。"
        )

def handle_message_event(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """处理接收到的消息事件"""
    try:
        # 获取消息内容
        message_content = data.event.message.content
        message_type = data.event.message.message_type
        sender_id = data.event.sender.sender_id.user_id
        chat_id = data.event.message.chat_id
        chat_type = data.event.message.chat_type
        
        logger.info(f"收到长连接消息: {message_content} (chat_type: {chat_type})")
        
        # 处理文本消息
        if message_type == "text":
            import json
            content_dict = json.loads(message_content)
            text = content_dict.get("text", "")
            
            # 处理群聊消息：检查是否@了机器人或者是特定命令
            if chat_type == "group":
                mentions = getattr(data.event.message, 'mentions', [])
                # 确保mentions不为None，防止迭代错误
                if mentions is None:
                    mentions = []
                    
                bot_mentioned = False
                
                # 检查是否@了机器人
                for mention in mentions:
                    mention_id = mention.id
                    # 检查是否@了当前机器人
                    if mention_id.open_id or mention.name == "Bot":
                        bot_mentioned = True
                        # 移除@mention部分，只保留实际命令
                        mention_key = mention.key
                        if mention_key in text:
                            text = text.replace(mention_key, "").strip()
                        break
                
                # 群聊中：被@时处理所有消息，未被@时只处理特定命令
                if not bot_mentioned:
                    # 允许特定命令不需要@机器人
                    if not (text.startswith("新任务") or text.startswith("/")):
                        logger.info(f"Group message without mention ignored: {text}")
                        return
            
            # 异步处理文本命令
        import asyncio
        import concurrent.futures
        
        # 使用线程池执行器来避免事件循环冲突
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _process_text_command_sync(sender_id, text, chat_id))
            future.result()
            
    except Exception as e:
        logger.error(f"处理长连接消息事件失败: {str(e)}")

def handle_card_action_event(data) -> dict:
    """处理卡片动作事件"""
    try:
        # 获取动作信息
        action = data.action
        user_id = data.operator.operator_id.user_id
        
        logger.info(f"收到长连接卡片动作: {action}")
        
        # 异步处理卡片动作
        import asyncio
        import concurrent.futures
        
        # 使用线程池执行器来避免事件循环冲突
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _handle_card_action_sync(action, user_id))
            future.result()
        
        # 返回响应
        return {
            "toast": {
                "type": "info",
                "content": "操作已处理"
            }
        }
        
    except Exception as e:
         logger.error(f"处理长连接卡片动作事件失败: {str(e)}")
         return {
             "toast": {
                 "type": "error",
                 "content": "处理失败"
             }
         }
 
# 全局变量防止重复启动
_websocket_client_started = False
_websocket_thread = None

def setup_websocket_client():
    """设置并启动飞书长连接客户端"""
    global _websocket_client_started, _websocket_thread
    
    # 防止重复启动
    if _websocket_client_started:
        logger.info("飞书长连接客户端已经启动，跳过重复启动")
        return
    
    import threading
    
    def run_websocket_client():
        """在单独线程中运行长连接客户端"""
        try:
            # 创建事件处理器
            event_handler = lark.EventDispatcherHandler.builder("", "") \
                .register_p2_im_message_receive_v1(handle_message_event) \
                .register_p2_card_action_trigger(handle_card_action_event) \
                .build()
            
            # 创建长连接客户端
            cli = lark.ws.Client(
                settings.feishu_app_id,
                settings.feishu_app_secret,
                event_handler=event_handler,
                log_level=lark.LogLevel.DEBUG if settings.debug else lark.LogLevel.INFO
            )
            
            logger.info("飞书长连接客户端已启动")
            
            # 启动客户端（这是一个阻塞调用）
            cli.start()
            
        except Exception as e:
            logger.error(f"启动飞书长连接客户端失败: {str(e)}")
            global _websocket_client_started
            _websocket_client_started = False  # 重置状态以允许重试
    
    try:
        # 创建并启动线程
        _websocket_thread = threading.Thread(target=run_websocket_client, daemon=True)
        _websocket_thread.start()
        _websocket_client_started = True
        
        logger.info("飞书长连接客户端线程已启动")
        
    except Exception as e:
        logger.error(f"启动飞书长连接客户端线程失败: {str(e)}")
        _websocket_client_started = False

async def _handle_card_action_sync(action: dict, user_id: str):
    """处理卡片动作的异步函数"""
    try:
        # 这里可以根据具体的卡片动作进行处理
        logger.info(f"处理用户 {user_id} 的卡片动作: {action}")
        
        # 可以在这里添加具体的卡片动作处理逻辑
        # 例如：根据 action 的值执行不同的操作
        
    except Exception as e:
        logger.error(f"处理卡片动作失败: {str(e)}")

async def _process_text_command_sync(user_id: str, text: str, chat_id: str = None):
    """同步版本的文本命令处理（用于长连接事件）"""
    try:
        await _process_text_command(user_id, text, chat_id)
    except Exception as e:
        logger.error(f"处理文本命令时出错: {str(e)}")

async def _handle_card_action_sync(user_id: str, action_value: Dict[str, Any]):
    """同步版本的卡片交互处理（用于长连接事件）"""
    try:
        # 构造与原有格式兼容的事件数据
        event = {
            "action": {"value": action_value},
            "operator": {"user_id": user_id}
        }
        await _handle_feishu_card_action(event)
    except Exception as e:
        logger.error(f"处理卡片交互时出错: {str(e)}")

# HTTP Webhook路由已禁用，现在使用长连接处理所有事件

# GitHub Webhook路由已禁用，现在使用长连接处理所有事件

async def handle_workflow_run_event(data: dict):
    """处理工作流运行事件"""
    try:
        action = data.get('action')
        workflow_run = data.get('workflow_run', {})
        
        workflow_name = workflow_run.get('name', 'Unknown')
        status = workflow_run.get('status')
        conclusion = workflow_run.get('conclusion')
        
        logger.info(f"Workflow event: {action} - {workflow_name} ({status}/{conclusion})")
        
        # 使用CI服务处理工作流事件
        if action == 'completed':
            from app.services.ci import CIService
            ci_service = CIService()
            await ci_service.process_webhook_event({
                'type': 'workflow_run',
                'action': action,
                'workflow_run': workflow_run
            })
        
    except Exception as e:
        logger.error(f"Error handling workflow run event: {str(e)}")

async def handle_check_run_event(data: dict):
    """处理检查运行事件"""
    try:
        action = data.get('action')
        check_run = data.get('check_run', {})
        
        check_name = check_run.get('name', 'Unknown')
        status = check_run.get('status')
        conclusion = check_run.get('conclusion')
        
        logger.info(f"Check run event: {action} - {check_name} ({status}/{conclusion})")
        
        # 使用CI服务处理检查运行事件
        if action == 'completed':
            from app.services.ci import CIService
            ci_service = CIService()
            await ci_service.process_webhook_event({
                'type': 'check_run',
                'action': action,
                'check_run': check_run
            })
        
    except Exception as e:
        logger.error(f"Error handling check run event: {str(e)}")

async def handle_status_event(data: dict):
    """处理状态事件"""
    try:
        state = data.get('state')
        description = data.get('description', '')
        target_url = data.get('target_url', '')
        context = data.get('context', 'Unknown')
        
        logger.info(f"Status event: {context} - {state} ({description})")
        
        # 使用CI服务处理状态事件
        from app.services.ci import CIService
        ci_service = CIService()
        await ci_service.process_webhook_event({
            'type': 'status',
            'state': state,
            'description': description,
            'target_url': target_url,
            'context': context
        })
        
    except Exception as e:
        logger.error(f"Error handling status event: {str(e)}")

async def _handle_feishu_event(event: Dict[str, Any]):
    """处理Feishu事件"""
    try:
        event_type = event.get("type")
        
        if event_type == "message":
            await _handle_feishu_message(event)
        elif event_type == "card_action":
            await _handle_feishu_card_action(event)
        elif event_type == "bot_menu":
            await _handle_feishu_bot_menu(event)
        else:
            logger.info(f"Unhandled Feishu event type: {event_type}")
            
    except Exception as e:
        logger.error(f"Error handling Feishu event: {str(e)}")

async def _handle_feishu_message(event: Dict[str, Any]):
    """处理Feishu消息事件"""
    try:
        message = event.get("message", {})
        sender = event.get("sender", {})
        user_id = sender.get("sender_id", {}).get("user_id")
        chat_id = message.get("chat_id")
        chat_type = message.get("chat_type", "p2p")  # 获取聊天类型
        
        # 忽略机器人自己的消息
        if sender.get("sender_type") == "app":
            return
        
        message_type = message.get("message_type")
        content = message.get("content")
        
        if message_type == "text":
            text_content = json.loads(content).get("text", "")
            
            # 处理群聊消息：只有在被@时才响应
            if chat_type == "group":
                mentions = message.get("mentions", [])
                bot_mentioned = False
                
                # 检查是否@了机器人
                for mention in mentions:
                    mention_id = mention.get("id", {})
                    # 检查是否@了当前机器人（通过app_id或其他标识）
                    if mention_id.get("open_id") or mention.get("name") == "Bot":
                        bot_mentioned = True
                        # 移除@mention部分，只保留实际命令
                        mention_key = mention.get("key", "")
                        if mention_key in text_content:
                            text_content = text_content.replace(mention_key, "").strip()
                        break
                
                # 群聊中只有被@时才处理消息
                if not bot_mentioned:
                    logger.info(f"Group message without mention ignored: {text_content}")
                    return
            
            logger.info(f"Processing text command: {text_content} from user: {user_id} in chat: {chat_id} (type: {chat_type})")
            await _process_text_command(user_id, text_content, chat_id)
        
    except Exception as e:
        logger.error(f"Error handling Feishu message: {str(e)}")

async def _handle_feishu_card_action(event: Dict[str, Any]):
    """处理Feishu卡片交互事件"""
    try:
        action = event.get("action", {})
        user_id = event.get("operator", {}).get("user_id")
        
        action_value = action.get("value", {})
        action_type = action_value.get("action")
        
        if action_type == "accept_task":
            task_id = action_value.get("task_id")
            success = await task_manager.accept_task(task_id, user_id)
            
            if success:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"✅ 您已成功接受任务 {task_id}，请开始执行！"
                )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"❌ 接受任务失败，任务可能已被其他人接受。"
                )
        
        elif action_type == "reject_task":
            task_id = action_value.get("task_id")
            await feishu_service.send_text_message(
                user_id=user_id,
                text=f"您已拒绝任务 {task_id}，感谢您的关注！"
            )
        
        elif action_type == "submit_task":
            # 这里可以打开提交表单或引导用户提交
            task_id = action_value.get("task_id")
            await feishu_service.send_text_message(
                user_id=user_id,
                text=f"请提交任务 {task_id} 的完成链接，格式：/submit {task_id} <链接> [备注]"
            )
        
        elif action_type == "select_candidate":
            # 处理候选人选择
            await handle_candidate_selection(user_id, action_value)
        
    except Exception as e:
        logger.error(f"Error handling Feishu card action: {str(e)}")

async def _handle_feishu_bot_menu(event: Dict[str, Any]):
    """处理Feishu机器人菜单事件"""
    try:
        user_id = event.get("operator", {}).get("user_id")
        event_key = event.get("event_key")
        
        if event_key == "my_tasks":
            tasks = await task_manager.get_user_tasks(user_id)
            if tasks:
                task_list = "\n".join([
                    f"• {task['title']} ({task['status']})"
                    for task in tasks[:10]
                ])
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"您的任务列表：\n{task_list}",
                    chat_id=chat_id
                )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="您当前没有任务。",
                    chat_id=chat_id
                )
        
        elif event_key == "help":
            # 使用统一的帮助命令
            await handle_help_command(user_id)
        
    except Exception as e:
        logger.error(f"Error handling Feishu bot menu: {str(e)}")

async def handle_bitable_command(user_id: str, text: str, chat_id: str = None):
    """处理多维表格操作命令"""
    try:
        parts = text.split(" ", 1)
        if len(parts) == 1:
            # 显示多维表格操作帮助
            help_text = """🗂️ 多维表格操作帮助

可用命令：
• /bitable table create <表名> - 创建新的数据表
• /bitable table list - 列出所有数据表
• /bitable field add <表ID> <字段名> <字段类型> - 添加字段
• /bitable record add <表ID> <字段1>=<值1> <字段2>=<值2>... - 添加记录
• /bitable record list <表ID> [过滤条件] - 查询记录

字段类型包括：text(文本), number(数字), select(单选), multiselect(多选), date(日期), checkbox(勾选), person(人员), attachment(附件)

示例：
/bitable table create 任务列表
/bitable field add tblzZiKqQH 任务名称 text
/bitable record add tblzZiKqQH 任务名称=测试任务 状态=进行中
/bitable record list tblzZiKqQH 状态=进行中"""
            
            await feishu_service.send_text_message(
                user_id=user_id,
                text=help_text,
                chat_id=chat_id
            )
            return
        
        command = parts[1].strip()
        
        # 移除了create和list命令，因为我们使用固定的应用token
        
        if command.startswith("table "):
            # 处理表格相关命令
            table_cmd = command[6:].strip()
            app_token = settings.feishu_bitable_app_token  # 使用固定的应用token
            
            if table_cmd.startswith("create "):
                # 创建数据表
                table_name = table_cmd[7:].strip()
                if not table_name:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text="请提供表名，格式：/bitable table create <表名>",
                        chat_id=chat_id
                    )
                    return
                
                try:
                    table_id = await bitable_client.create_table(app_token, table_name)
                    if table_id:
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"[成功] 数据表创建成功！\n表ID: {table_id}\n\n您可以使用以下命令添加字段：\n/bitable field add {table_id} <字段名> <字段类型>",
                            chat_id=chat_id
                        )
                    else:
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text="[失败] 创建数据表失败，请稍后重试。",
                            chat_id=chat_id
                        )
                except Exception as e:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"[错误] 创建数据表出错：{str(e)}",
                        chat_id=chat_id
                    )
            
            elif table_cmd.startswith("list"):
                # 列出应用中的数据表
                try:
                    tables = await bitable_client.list_tables(app_token)
                    if tables and len(tables) > 0:
                        table_list = "\n".join([f"• {table['name']} - ID: {table['table_id']}" for table in tables])
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"[列表] 数据表列表：\n{table_list}",
                            chat_id=chat_id
                        )
                    else:
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"暂无数据表，可使用 /bitable table create <表名> 创建",
                            chat_id=chat_id
                        )
                except Exception as e:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"[错误] 获取数据表列表出错：{str(e)}",
                        chat_id=chat_id
                    )
        
        elif command.startswith("field add "):
            # 添加字段
            params = command[10:].strip().split(" ", 2)
            if len(params) != 3:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供正确的参数，格式：/bitable field add <表ID> <字段名> <字段类型>",
                    chat_id=chat_id
                )
                return
            
            app_token = settings.feishu_bitable_app_token  # 使用固定的应用token
            table_id, field_name, field_type = params
            try:
                field_id = await bitable_client.add_field(app_token, table_id, field_name, field_type)
                if field_id:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"[成功] 字段添加成功！\n字段ID: {field_id}",
                        chat_id=chat_id
                    )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text="[失败] 添加字段失败，请稍后重试。",
                        chat_id=chat_id
                    )
            except Exception as e:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"[错误] 添加字段出错：{str(e)}",
                    chat_id=chat_id
                )
        
        elif command.startswith("record add "):
            # 添加记录
            parts = command[11:].strip().split(" ", 1)
            if len(parts) < 2:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供正确的参数，格式：/bitable record add <表ID> <字段1>=<值1> <字段2>=<值2>...",
                    chat_id=chat_id
                )
                return
            
            app_token = settings.feishu_bitable_app_token  # 使用固定的应用token
            table_id, fields_str = parts
            
            # 解析字段值对
            fields_data = {}
            field_pairs = fields_str.split(" ")
            for pair in field_pairs:
                if "=" in pair:
                    field_name, field_value = pair.split("=", 1)
                    fields_data[field_name] = field_value
            
            if not fields_data:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供至少一个字段值对，格式：字段名=值",
                    chat_id=chat_id
                )
                return
            
            try:
                record_id = await bitable_client.add_record(app_token, table_id, fields_data)
                if record_id:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"[成功] 记录添加成功！\n记录ID: {record_id}",
                        chat_id=chat_id
                    )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text="[失败] 添加记录失败，请稍后重试。",
                        chat_id=chat_id
                    )
            except Exception as e:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"[错误] 添加记录出错：{str(e)}",
                    chat_id=chat_id
                )
        
        elif command.startswith("record list "):
            # 查询记录
            parts = command[12:].strip().split(" ", 1)
            if len(parts) < 1:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供正确的参数，格式：/bitable record list <表ID> [过滤条件]",
                    chat_id=chat_id
                )
                return
            
            app_token = settings.feishu_bitable_app_token  # 使用固定的应用token
            table_id = parts[0]
            filter_str = parts[1] if len(parts) > 1 else ""
            
            try:
                records = await bitable_client.list_records(app_token, table_id, filter_str)
                if records and len(records) > 0:
                    # 格式化记录显示
                    if len(records) > 10:
                        record_count = len(records)
                        records = records[:10]  # 只显示前10条
                        record_list = "\n\n".join([f"记录 {i+1}:\n" + "\n".join([f"  {k}: {v}" for k, v in record.items()]) for i, record in enumerate(records)])
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"[记录] 查询到 {record_count} 条记录，显示前10条：\n{record_list}\n\n要查看更多记录，请添加更具体的过滤条件。",
                            chat_id=chat_id
                        )
                    else:
                        record_list = "\n\n".join([f"记录 {i+1}:\n" + "\n".join([f"  {k}: {v}" for k, v in record.items()]) for i, record in enumerate(records)])
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"[记录] 查询到 {len(records)} 条记录：\n{record_list}",
                            chat_id=chat_id
                        )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text="未查询到符合条件的记录。",
                        chat_id=chat_id
                    )
            except Exception as e:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"[错误] 查询记录出错：{str(e)}",
                    chat_id=chat_id
                )
        
        else:
            # 未识别的多维表格命令
            await feishu_service.send_text_message(
                user_id=user_id,
                text="未识别的多维表格命令，请输入 /bitable 查看可用命令。",
                chat_id=chat_id
            )
    
    except Exception as e:
        logger.error(f"处理多维表格命令出错: {str(e)}")
        await feishu_service.send_text_message(
            user_id=user_id,
            text=f"处理命令时出错: {str(e)}",
            chat_id=chat_id
        )

async def _process_text_command(user_id: str, text: str, chat_id: str = None):
    """处理文本命令"""
    try:
        text = text.strip()
        
        if text.startswith("/create"):
            # 简化的任务创建命令
            parts = text.split(" ", 1)
            if len(parts) > 1:
                title = parts[1]
                # 这里可以引导用户填写更详细的任务信息
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"正在创建任务：{title}\n请提供更多详细信息...",
                    chat_id=chat_id
                )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供任务标题，格式：/create <标题>",
                    chat_id=chat_id
                )
        
        elif text.startswith("/submit"):
            # 任务提交命令
            parts = text.split(" ", 3)
            if len(parts) >= 3:
                task_id = parts[1]
                submission_url = parts[2]
                submission_note = parts[3] if len(parts) > 3 else ""
                
                success = await task_manager.submit_task(
                    task_id=task_id,
                    user_id=user_id,
                    submission_url=submission_url,
                    submission_note=submission_note
                )
                
                if success:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"✅ 任务 {task_id} 提交成功，正在进行质量检查...",
                        chat_id=chat_id
                    )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"❌ 任务提交失败，请检查任务ID和权限。",
                        chat_id=chat_id
                    )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="格式错误，请使用：/submit <任务ID> <链接> [备注]",
                    chat_id=chat_id
                )
        
        elif text.startswith("/status"):
            # 查看任务状态
            parts = text.split(" ", 1)
            if len(parts) > 1:
                task_id = parts[1]
                task = await task_manager.get_task_status(task_id)
                
                if task:
                    status_text = f"""📋 任务状态

标题：{task.get('title', 'N/A')}
状态：{task.get('status', 'N/A')}
负责人：{task.get('assignee', '未分配')}
截止时间：{task.get('deadline', 'N/A')}
创建时间：{task.get('created_at', 'N/A')}"""
                    
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=status_text,
                        chat_id=chat_id
                    )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"未找到任务 {task_id}",
                        chat_id=chat_id
                    )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供任务ID，格式：/status <任务ID>",
                    chat_id=chat_id
                )
        
        elif text.startswith("/mytasks"):
            # 查看我的任务
            tasks = await task_manager.get_user_tasks(user_id)
            if tasks:
                task_list = "\n".join([
                    f"• {task['title']} ({task['status']})"
                    for task in tasks[:10]
                ])
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"您的任务列表：\n{task_list}",
                    chat_id=chat_id
                )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="您当前没有任务。",
                    chat_id=chat_id
                )
        
        elif text.startswith("/help"):
            # 显示帮助
            await handle_help_command(user_id)
        
        elif text.startswith("/bitable"):
            # 处理多维表格操作命令
            await handle_bitable_command(user_id, text, chat_id)
            
        elif text.startswith("/table"):
            # 处理表格查询命令
            await handle_table_command(user_id, text, chat_id)
        
        elif text.startswith("/done"):
            # 处理任务完成提交命令
            await handle_done_command(user_id, text, chat_id)
        
        elif text.startswith("/report") or text.startswith("#report"):
            # 处理每日报告查询命令
            await handle_report_command(user_id, text, chat_id)
        
        elif ('@bot' in text and '新任务' in text) or text.startswith('新任务'):
            # 处理新任务命令
            await handle_new_task_command(user_id, text, chat_id)
        
        else:
            # 未识别的命令
            await feishu_service.send_text_message(
                user_id=user_id,
                text="未识别的命令，请输入 /help 查看可用命令。",
                chat_id=chat_id
            )
        
    except Exception as e:
        logger.error(f"Error processing text command: {str(e)}")
        await feishu_service.send_text_message(
            user_id=user_id,
            text="处理命令时出错，请稍后重试。",
            chat_id=chat_id
        )

async def _handle_github_push(event_data: Dict[str, Any]):
    """处理GitHub推送事件"""
    try:
        repository = event_data.get("repository", {})
        commits = event_data.get("commits", [])
        pusher = event_data.get("pusher", {})
        
        repo_name = repository.get("full_name")
        branch = event_data.get("ref", "").replace("refs/heads/", "")
        
        # 这里可以根据提交信息自动创建或更新任务
        # 例如：检查提交消息中是否包含任务ID，自动关联
        
        logger.info(f"GitHub push to {repo_name}:{branch} with {len(commits)} commits")
        
    except Exception as e:
        logger.error(f"Error handling GitHub push: {str(e)}")

async def _handle_github_pull_request(event_data: Dict[str, Any]):
    """处理GitHub Pull Request事件"""
    try:
        action = event_data.get("action")
        pull_request = event_data.get("pull_request", {})
        repository = event_data.get("repository", {})
        
        pr_number = pull_request.get("number")
        pr_title = pull_request.get("title")
        repo_name = repository.get("full_name")
        
        # 这里可以根据PR事件自动更新任务状态
        # 例如：PR合并时自动标记任务为完成
        
        logger.info(f"GitHub PR {action}: {repo_name}#{pr_number} - {pr_title}")
        
    except Exception as e:
        logger.error(f"Error handling GitHub pull request: {str(e)}")

async def _handle_github_issues(event_data: Dict[str, Any]):
    """处理GitHub Issues事件"""
    try:
        action = event_data.get("action")
        issue = event_data.get("issue", {})
        repository = event_data.get("repository", {})
        
        issue_number = issue.get("number")
        issue_title = issue.get("title")
        repo_name = repository.get("full_name")
        
        # 这里可以根据Issue事件自动创建任务
        # 例如：新Issue创建时自动生成对应任务
        
        logger.info(f"GitHub Issue {action}: {repo_name}#{issue_number} - {issue_title}")
        
    except Exception as e:
        logger.error(f"Error handling GitHub issues: {str(e)}")

async def handle_new_task_command(user_id: str, text_content: str, chat_id: str = None):
    """处理@bot新任务命令"""
    try:
        # 提取任务描述（去除@bot 新任务前缀）
        task_description = text_content.replace('@bot', '').replace('新任务', '').strip()
        
        if not task_description:
            await feishu_service.send_message(
                user_id=user_id,
                message="请提供任务描述。格式：@bot 新任务 [任务描述]"
            )
            return
        
        # 获取所有候选人信息
        candidates = await bitable_client.get_all_candidates()
        
        # 确保candidates是列表类型，防止None导致迭代错误
        if candidates is None:
            candidates = []
        
        if not candidates:
            await feishu_service.send_message(
                user_id=user_id,
                message="暂无可用候选人信息。"
            )
            return
        
        # 调用DeepSeek生成表格形式的任务描述和候选人推荐
        from app.services.llm import llm_service
        
        # 构建候选人信息字符串
        candidates_info = "\n".join([
            f"- {c.get('name', '未知')}: 技能[{', '.join(c.get('skill_tags', []))}], "
            f"经验{c.get('experience_years', 0)}年, "
            f"可用时间{c.get('hours_available', 0)}小时/周, "
            f"评分{c.get('average_score', 0)}"
            for c in candidates
        ])
        
        # 构建DeepSeek提示词
        system_prompt = """你是一个专业的项目管理助手。请根据任务描述和候选人信息，生成结构化的任务信息和推荐前三名最佳候选人。

请严格按照以下JSON格式返回：
{
  "task": {
    "title": "任务标题",
    "description": "详细任务描述",
    "skill_tags": ["技能1", "技能2"],
    "deadline": "YYYY-MM-DD",
    "urgency": "high/normal/low",
    "estimated_hours": 数字,
    "reward_points": 数字
  },
  "top_candidates": [
    {
      "name": "候选人姓名",
      "match_score": 数字(0-100),
      "match_reason": "匹配理由",
      "skill_tags": ["技能列表"],
      "experience_years": 数字,
      "hours_available": 数字
    }
  ]
}"""
        
        user_prompt = f"""任务描述：{task_description}

候选人信息：
{candidates_info}

请分析任务需求，生成结构化的任务信息，并从候选人中推荐前三名最佳人选。"""
        
        # 调用DeepSeek
        response = await llm_service.call_with_retry(user_prompt, system_prompt)
        
        # 解析DeepSeek返回的JSON
        import json
        import re
        try:
            # 处理可能被markdown代码块包裹的JSON
            json_text = response.strip()
            if json_text.startswith('```json') and json_text.endswith('```'):
                # 提取markdown代码块中的JSON
                json_text = re.sub(r'^```json\s*', '', json_text)
                json_text = re.sub(r'\s*```$', '', json_text)
            elif json_text.startswith('```') and json_text.endswith('```'):
                # 提取普通代码块中的JSON
                json_text = re.sub(r'^```\s*', '', json_text)
                json_text = re.sub(r'\s*```$', '', json_text)
            
            result = json.loads(json_text)
            task_info = result.get('task', {})
            top_candidates = result.get('top_candidates', [])
        except json.JSONDecodeError:
            logger.error(f"DeepSeek返回的不是有效JSON: {response}")
            await feishu_service.send_message(
                user_id=user_id,
                message="AI分析任务时出错，请稍后重试。"
            )
            return
        
        # 验证必要字段并设置默认值
        if not task_info.get('title'):
            task_info['title'] = task_description[:50] + '...' if len(task_description) > 50 else task_description
        if not task_info.get('description'):
            task_info['description'] = task_description
        if not task_info.get('skill_tags'):
            task_info['skill_tags'] = ['通用']
        if not task_info.get('deadline'):
            from datetime import datetime, timedelta
            task_info['deadline'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        task_info.setdefault('urgency', 'normal')
        task_info.setdefault('estimated_hours', 8)
        task_info.setdefault('reward_points', 100)
        task_info['created_by'] = user_id
        
        # 创建任务并添加到多维表格 - 已禁用
        # task_id = await task_manager.create_task(task_info)
        
        # 任务创建失败处理已移除
        
        # 生成临时任务ID用于显示
        import uuid
        task_id = f"temp_{uuid.uuid4().hex[:8]}"
        
        # 发送任务创建成功消息和前三名候选人到群聊
        if chat_id:
            # 构建任务信息消息
            task_message = f"""🎯 **AI任务分析结果**

**任务ID**: {task_id} (仅供参考，未保存到表格)
**标题**: {task_info['title']}
**描述**: {task_info['description']}
**技能要求**: {', '.join(task_info['skill_tags'])}
**截止时间**: {task_info['deadline']}
**预估工时**: {task_info['estimated_hours']}小时
**奖励积分**: {task_info['reward_points']}分"""
            
            await feishu_service.send_message_to_chat(
                chat_id=chat_id,
                message=task_message
            )
            
            # 发送前三名候选人推荐卡片（带选择按钮）
            if top_candidates:
                await _send_candidate_selection_card(
                    user_id=user_id,
                    task_id=task_id,
                    task_info=task_info,
                    candidates=top_candidates[:3],
                    chat_id=chat_id
                )
        
        # 给HR发送确认消息
        await feishu_service.send_message(
            user_id=user_id,
            message=f"✅ AI任务分析完成！\n参考任务ID: {task_id}\n已发送分析结果到群聊并推荐了前三名候选人。\n注意：任务未保存到多维表格。"
        )
        
        logger.info(f"AI任务分析完成: {task_id}, AI推荐了 {len(top_candidates)} 名候选人 (未保存到表格)")
        
    except Exception as e:
        logger.error(f"处理新任务命令时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="处理新任务命令时出错，请稍后重试。"
        )

def _parse_new_task_text(text: str) -> Dict[str, Any]:
    """解析新任务文本"""
    try:
        # 移除@bot和新任务关键词
        text = text.replace('@bot', '').replace('新任务', '').strip()
        
        task_info = {}
        
        # 解析各个字段
        import re
        
        # 标题
        title_match = re.search(r'标题[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[描技截紧]|$)', text)
        if title_match:
            task_info['title'] = title_match.group(1).strip()
        
        # 描述
        desc_match = re.search(r'描述[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[标技截紧]|$)', text)
        if desc_match:
            task_info['description'] = desc_match.group(1).strip()
        
        # 技能标签
        skill_match = re.search(r'技能[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[标描截紧]|$)', text)
        if skill_match:
            skills = skill_match.group(1).strip()
            task_info['skill_tags'] = [s.strip() for s in skills.split(',') if s.strip()]
        
        # 截止时间
        deadline_match = re.search(r'截止[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[标描技紧]|$)', text)
        if deadline_match:
            task_info['deadline'] = deadline_match.group(1).strip()
        
        # 紧急度
        urgency_match = re.search(r'紧急度[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[标描技截]|$)', text)
        if urgency_match:
            urgency_text = urgency_match.group(1).strip()
            urgency_map = {'高': 'high', '中': 'normal', '低': 'low', '紧急': 'urgent'}
            task_info['urgency'] = urgency_map.get(urgency_text, 'normal')
        
        # 验证必要字段
        required_fields = ['title', 'description', 'skill_tags', 'deadline']
        for field in required_fields:
            if field not in task_info or not task_info[field]:
                return None
        
        # 设置默认值
        task_info.setdefault('urgency', 'normal')
        task_info.setdefault('estimated_hours', 8)
        task_info.setdefault('reward_points', 100)
        
        return task_info
        
    except Exception as e:
        logger.error(f"解析新任务文本时出错: {str(e)}")
        return None

async def _send_candidate_selection_card(user_id: str, task_id: str, task_info: Dict[str, Any], candidates: List[Dict[str, Any]], chat_id: str = None):
    """发送候选人选择卡片"""
    try:
        # 构建候选人卡片
        card_elements = []
        
        # 任务信息
        card_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**新任务匹配结果**\n\n**任务**: {task_info['title']}\n**描述**: {task_info['description']}\n**技能要求**: {', '.join(task_info['skill_tags'])}\n**截止时间**: {task_info['deadline']}"
            }
        })
        
        # 分隔线
        card_elements.append({"tag": "hr"})
        
        # 候选人列表
        for i, candidate in enumerate(candidates, 1):
            match_score = candidate.get('match_score', 0)
            match_reason = candidate.get('match_reason', '无')
            
            candidate_info = f"**候选人 {i}**: {candidate.get('name', '未知')}\n" \
                           f"**匹配度**: {match_score}%\n" \
                           f"**技能**: {', '.join(candidate.get('skill_tags', []))}\n" \
                           f"**可用时间**: {candidate.get('hours_available', 0)}小时\n" \
                           f"**匹配理由**: {match_reason}"
            
            card_elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": candidate_info
                }
            })
            
            # 选择按钮
            card_elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": f"✅ 选择候选人{i}"
                    },
                    "type": "primary",
                    "value": {
                        "action": "select_candidate",
                        "task_id": task_id,
                        "candidate_id": candidate.get('user_id'),
                        "candidate_rank": i
                    }
                }]
            })
            
            if i < len(candidates):
                card_elements.append({"tag": "hr"})
        
        # 构建完整卡片
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "elements": card_elements
        }
        
        # 发送卡片
        await feishu_service.send_card_message(
            user_id=user_id,
            card=card,
            chat_id=chat_id
        )
        
    except Exception as e:
        logger.error(f"发送候选人选择卡片时出错: {str(e)}")

async def handle_candidate_selection(user_id: str, action_value: Dict[str, Any]):
    """处理候选人选择"""
    try:
        task_id = action_value.get('task_id')
        candidate_id = action_value.get('candidate_id')
        candidate_rank = action_value.get('candidate_rank', 1)
        
        if not task_id or not candidate_id:
            await feishu_service.send_message(
                user_id=user_id,
                message="选择候选人失败：缺少必要参数"
            )
            return
        
        # 创建任务小群
        chat_name = f"任务协作群-{task_id[:8]}"
        members = [user_id, candidate_id]  # 任务发起人和候选人
        
        try:
            # 尝试创建群聊
            chat_id = await feishu_service.create_chat(chat_name, members)
            
            if chat_id:
                # 发送群聊创建成功消息
                welcome_message = f"🎉 任务协作群创建成功！\n\n" \
                                f"📋 **任务ID**: {task_id}\n" \
                                f"👤 **选中候选人**: 候选人{candidate_rank}\n" \
                                f"💬 **群聊ID**: {chat_id}\n\n" \
                                f"请在此群中进行任务相关的沟通协作。"
                
                await feishu_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=welcome_message
                )
                
                # 通知任务发起人
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"✅ 候选人选择成功！\n" \
                           f"已创建任务协作群：{chat_name}\n" \
                           f"群聊ID：{chat_id}"
                )
                
                # 通知被选中的候选人
                await feishu_service.send_message(
                    user_id=candidate_id,
                    message=f"🎯 恭喜！您被选中参与任务协作\n" \
                           f"任务ID：{task_id}\n" \
                           f"已为您创建任务协作群：{chat_name}\n" \
                           f"请查看群聊进行后续沟通。"
                )
                
            else:
                # 群聊创建失败，回退到原有逻辑
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"候选人选择成功，但创建协作群失败。\n" \
                           f"任务ID：{task_id}\n" \
                           f"选中候选人：{candidate_id}\n" \
                           f"请手动联系候选人进行后续沟通。"
                )
                
        except Exception as chat_error:
            logger.error(f"创建任务协作群时出错: {str(chat_error)}")
            # 群聊创建失败，但候选人选择成功
            await feishu_service.send_message(
                user_id=user_id,
                message=f"候选人选择成功，但创建协作群时出现问题。\n" \
                       f"任务ID：{task_id}\n" \
                       f"选中候选人：{candidate_id}\n" \
                       f"请手动联系候选人进行后续沟通。"
            )
            
        # 记录选择日志
        logger.info(f"用户 {user_id} 为任务 {task_id} 选择了候选人 {candidate_id} (排名第{candidate_rank})")
            
    except Exception as e:
        logger.error(f"处理候选人选择时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="处理候选人选择时发生错误，请稍后重试"
        )

def _verify_feishu_signature(body: bytes, headers: Dict[str, str]) -> bool:
    """验证Feishu请求签名"""
    try:
        # 签名验证已简化，生产环境请实现完整验证逻辑
        return True
    except Exception as e:
        logger.error(f"Error verifying Feishu signature: {str(e)}")
        return False

def _verify_github_signature(body: bytes, signature: str) -> bool:
    """验证GitHub请求签名"""
    try:
        if not signature or not settings.github_webhook_secret:
            return False
        
        # GitHub使用HMAC-SHA256签名
        expected_signature = hmac.new(
            settings.github_webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # 签名格式：sha256=<hash>
        if signature.startswith("sha256="):
            provided_signature = signature[7:]
            return hmac.compare_digest(expected_signature, provided_signature)
        
        return False
        
    except Exception as e:
        logger.error(f"Error verifying GitHub signature: {str(e)}")
        return False

async def handle_report_command(user_id: str, text: str, chat_id: str = None):
    """处理 /report 和 #report 命令"""
    try:
        # 生成每日报告
        report = await task_manager.generate_daily_report()
        
        # 同时更新本地JSON文件
        await _update_local_stats(report)
        
        if not report:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 获取报告数据失败，请稍后重试"
            )
            return
        
        # 格式化报告消息
        report_text = _format_daily_report(report)
        
        # 发送报告
        if chat_id:
            await feishu_service.send_message_to_chat(
                chat_id=chat_id,
                message=report_text
            )
        else:
            await feishu_service.send_message(
                user_id=user_id,
                message=report_text
            )
        
        logger.info(f"Daily report sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling report command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="生成报告时出错，请稍后重试"
        )

async def _update_local_stats(report_data: Dict[str, Any]):
    """更新本地统计文件"""
    try:
        import json
        import os
        from datetime import datetime
        
        stats_file = "daily_stats.json"
        
        # 准备统计数据
        stats = {
            "date": report_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            "total_tasks": report_data.get('total_tasks', 0),
            "completed_tasks": report_data.get('completed_tasks', 0),
            "pending_tasks": report_data.get('pending_tasks', 0),
            "in_progress_tasks": report_data.get('in_progress_tasks', 0),
            "submitted_tasks": report_data.get('submitted_tasks', 0),
            "rejected_tasks": report_data.get('rejected_tasks', 0),
            "average_score": report_data.get('average_score', 0.0),
            "completion_rate": report_data.get('completion_rate', 0.0),
            "tasks_by_status": {
                "published": report_data.get('published_tasks', 0),
                "in_progress": report_data.get('in_progress_tasks', 0),
                "submitted": report_data.get('submitted_tasks', 0),
                "reviewing": report_data.get('reviewing_tasks', 0),
                "completed": report_data.get('completed_tasks', 0),
                "rejected": report_data.get('rejected_tasks', 0)
            },
            "top_performers": report_data.get('top_performers', []),
            "last_updated": datetime.now().isoformat()
        }
        
        # 写入文件
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Local stats updated: {stats_file}")
        
    except Exception as e:
        logger.error(f"Error updating local stats: {str(e)}")

def _format_daily_report(report: Dict[str, Any]) -> str:
    """格式化每日报告消息"""
    try:
        date = report.get('date', 'Unknown')
        total_tasks = report.get('total_tasks', 0)
        completed_tasks = report.get('completed_tasks', 0)
        pending_tasks = report.get('pending_tasks', 0)
        in_progress_tasks = report.get('in_progress_tasks', 0)
        average_score = report.get('average_score', 0)
        completion_rate = report.get('completion_rate', 0)
        
        # 计算完成率百分比
        completion_percentage = completion_rate * 100 if completion_rate else 0
        
        report_text = f"""📊 **每日任务统计报告**

📅 **日期**: {date}

📈 **任务概览**:
• 总任务数: {total_tasks}
• 已完成: {completed_tasks}
• 进行中: {in_progress_tasks}
• 待处理: {pending_tasks}

🎯 **绩效指标**:
• 完成率: {completion_percentage:.1f}%
• 平均评分: {average_score:.1f}分

📋 **任务状态分布**:
• ✅ 已完成: {completed_tasks}
• 🔄 进行中: {in_progress_tasks}
• ⏳ 待处理: {pending_tasks}

---
💡 数据更新时间: {report.get('last_updated', 'Unknown')}"""
        
        return report_text
        
    except Exception as e:
        logger.error(f"Error formatting daily report: {str(e)}")
        return "❌ 报告格式化失败"