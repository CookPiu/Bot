"""飞书服务模块"""
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import *
    LARK_SDK_AVAILABLE = True
except ImportError:
    LARK_SDK_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Lark SDK not available")
from app.config import settings

logger = logging.getLogger(__name__)

class FeishuService:
    def __init__(self):
        self.app_id = settings.feishu_app_id
        self.app_secret = settings.feishu_app_secret
        
        if not LARK_SDK_AVAILABLE:
            raise ImportError("Lark SDK is required but not available. Please install lark-oapi package.")
        
        if not self.app_id or not self.app_secret:
            raise ValueError("Feishu app_id and app_secret are required")
        
        # 使用真实的飞书SDK
        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()
        
        logger.info("FeishuService initialized with real Lark SDK")
    
    async def send_message(self, user_id: str, message: str):
        """发送消息给用户"""
        try:
            # 构建消息体
            request = CreateMessageRequest.builder() \
                .receive_id_type("user_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(user_id)
                    .msg_type("text")
                    .content(json.dumps({"text": message}, ensure_ascii=False))
                    .build()) \
                .build()
            
            # 发送消息
            response = self.client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(f"发送消息失败: {response.msg}")
                return False
            
            logger.info(f"消息发送成功给用户 {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息异常: {str(e)}")
            return False
    
    async def send_message_to_chat(self, chat_id: str, message: str):
        """发送消息到聊天群组"""
        try:
            # 构建消息体
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("text")
                    .content(json.dumps({"text": message}, ensure_ascii=False))
                    .build()) \
                .build()
            
            # 发送消息
            response = self.client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(f"发送消息到聊天群组失败: {response.msg}")
                return False
            
            logger.info(f"消息发送成功到聊天群组 {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息到聊天群组异常: {str(e)}")
            return False
    
    async def send_text_message(self, user_id: str = None, text: str = "", chat_id: str = None):
        """发送文本消息给用户或聊天群组"""
        if chat_id:
            return await self.send_message_to_chat(chat_id, text)
        elif user_id:
            return await self.send_message(user_id, text)
        else:
            logger.error("必须提供user_id或chat_id")
            return False
    
    async def send_candidate_cards(self, chat_id: str, candidates: List[Dict[str, Any]], task_id: str) -> bool:
        """发送候选人卡片消息"""
        try:
            # 构建候选人卡片内容
            card_content = {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**任务ID: {task_id}**\n推荐候选人:",
                            "tag": "lark_md"
                        }
                    }
                ]
            }
            
            # 添加候选人信息
            for i, candidate in enumerate(candidates[:3]):
                card_content["elements"].append({
                    "tag": "div",
                    "text": {
                        "content": f"{i+1}. {candidate.get('name', 'Unknown')} - 技能: {', '.join(candidate.get('skills', []))}",
                        "tag": "lark_md"
                    }
                })
            
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("interactive")
                    .content(json.dumps(card_content))
                    .build()) \
                .build()
            
            response = self.client.im.v1.message.create(request)
            
            if response.success():
                logger.info(f"Candidate cards sent successfully to {chat_id} for task {task_id}")
                return True
            else:
                logger.error(f"Failed to send candidate cards: {response.code} - {response.msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending candidate cards: {str(e)}")
            return False
    
    async def send_task_notification(self, user_id: str, task_data: Dict[str, Any]) -> bool:
        """发送任务通知"""
        try:
            # 构建任务通知卡片
            card_content = {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**新任务通知**\n任务: {task_data.get('title', '')}\n描述: {task_data.get('description', '')}\n截止时间: {task_data.get('deadline', '')}\n优先级: {task_data.get('priority', 'medium')}",
                            "tag": "lark_md"
                        }
                    }
                ]
            }
            
            request = CreateMessageRequest.builder() \
                .receive_id_type("user_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(user_id)
                    .msg_type("interactive")
                    .content(json.dumps(card_content))
                    .build()) \
                .build()
            
            response = self.client.im.v1.message.create(request)
            
            if response.success():
                logger.info(f"Task notification sent successfully to {user_id}")
                return True
            else:
                logger.error(f"Failed to send task notification: {response.code} - {response.msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending task notification: {str(e)}")
            return False
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        # TODO: 实现真实的用户信息获取
        raise NotImplementedError("get_user_info method needs to be implemented with real Lark SDK")
    
    async def get_chat_members(self, chat_id: str) -> List[str]:
        """获取群聊成员列表"""
        # TODO: 实现真实的群聊成员获取
        raise NotImplementedError("get_chat_members method needs to be implemented with real Lark SDK")
    
    async def create_chat(self, name: str, members: List[str]) -> Optional[str]:
        """创建群聊"""
        # TODO: 实现真实的群聊创建
        raise NotImplementedError("create_chat method needs to be implemented with real Lark SDK")
    
    async def send_approval_card(self, chat_id: str, task_data: Dict[str, Any], candidates: List[Dict[str, Any]]) -> bool:
        """发送审批卡片"""
        # TODO: 实现真实的审批卡片发送
        raise NotImplementedError("send_approval_card method needs to be implemented with real Lark SDK")
    
    async def handle_card_action(self, action_data: Dict[str, Any]) -> bool:
        """处理卡片交互动作"""
        # TODO: 实现真实的卡片交互处理
        raise NotImplementedError("handle_card_action method needs to be implemented with real Lark SDK")
    
    async def send_daily_report(self, chat_id: str, report_data: Dict[str, Any]) -> bool:
        """发送日报"""
        # TODO: 实现真实的日报发送
        raise NotImplementedError("send_daily_report method needs to be implemented with real Lark SDK")
    
    async def get_message_history(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取消息历史"""
        # TODO: 实现真实的消息历史获取
        raise NotImplementedError("get_message_history method needs to be implemented with real Lark SDK")

# 创建全局实例
feishu_service = FeishuService()