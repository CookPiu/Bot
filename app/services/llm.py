import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import asyncio
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class LLMBackend(ABC):
    """LLM后端抽象基类"""
    
    @abstractmethod
    async def call(self, prompt: str, system_prompt: str = "") -> str:
        """调用LLM API"""
        pass

class DeepSeekBackend(LLMBackend):
    """DeepSeek API后端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    async def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                    raise Exception(f"DeepSeek API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            raise

class GeminiBackend(LLMBackend):
    """Google Gemini API后端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    async def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                response = await client.post(
                    f"{self.base_url}?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [{"text": full_prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 2000
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                    raise Exception(f"Gemini API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            raise

class OpenAIBackend(LLMBackend):
    """OpenAI API后端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    async def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    raise Exception(f"OpenAI API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise

class LLMService:
    """LLM服务管理器"""
    
    def __init__(self):
        self.backends = {}
        self._initialize_backends()
    
    def _initialize_backends(self):
        """初始化可用的LLM后端"""
        if settings.deepseek_key:
            self.backends['deepseek'] = DeepSeekBackend(settings.deepseek_key)
            logger.info("DeepSeek backend initialized")
        
        if settings.gemini_key:
            self.backends['gemini'] = GeminiBackend(settings.gemini_key)
            logger.info("Gemini backend initialized")
        
        if settings.openai_key:
            self.backends['openai'] = OpenAIBackend(settings.openai_key)
            logger.info("OpenAI backend initialized")
        
        if not self.backends:
            logger.warning("No LLM backends available")
    
    async def call_with_retry(self, prompt: str, system_prompt: str = "", 
                             preferred_model: str = None) -> str:
        """LLM调用（已移除重试机制）"""
        model_order = [preferred_model] if preferred_model else []
        model_order.extend([m for m in self.backends.keys() if m != preferred_model])
        
        last_error = None
        
        for model_name in model_order:
            if model_name not in self.backends:
                continue
                
            backend = self.backends[model_name]
            
            try:
                logger.info(f"Calling {model_name}")
                result = await backend.call(prompt, system_prompt)
                logger.info(f"Successfully called {model_name}")
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Failed to call {model_name}: {str(e)}")
                # 继续尝试下一个模型，不重试当前模型
        
        raise Exception(f"All LLM backends failed. Last error: {str(last_error)}")
    
    async def match_candidates(self, task_requirements: Dict[str, Any], 
                             candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """候选人匹配"""
        try:
            # 构建系统提示词
            system_prompt = """你是智能人才匹配助手。根据任务需求和候选人信息，分析匹配度并返回Top-3推荐。

候选人数据字段说明：
- name: 候选人姓名
- skill_tags: 技能标签列表（如：['go', 'python', 'java']）
- score: 候选人评分（0-100）
- performance: 历史表现评级（1-5）
- experience: 工作经验（年数）
- user_id: 候选人唯一标识

评分标准：
1. 技能匹配度 (40%): 候选人skill_tags与任务要求的匹配程度
2. 综合能力 (30%): 基于score和performance的综合评估
3. 经验匹配 (20%): experience是否满足任务复杂度要求
4. 可用性 (10%): 候选人当前状态和可用性

请返回JSON格式，包含top-3的候选人user_id和匹配分数(0-100)。"""
            
            # 构建用户提示词
            skill_tags = task_requirements.get('skill_tags', [])
            deadline = task_requirements.get('deadline', '')
            
            candidates_text = "\n".join([
                f"{i+1}) {json.dumps(candidate, ensure_ascii=False)}"
                for i, candidate in enumerate(candidates)
            ])
            
            user_prompt = f"""任务需求:
- 技能要求: {skill_tags}
- 截止时间: {deadline}
- 紧急程度: {task_requirements.get('urgency', '普通')}

候选人列表:
{candidates_text}

请仔细分析每个候选人的skill_tags字段与任务技能要求的匹配度，结合score、performance、experience等指标进行综合评估。

请返回JSON数组格式的匹配结果，例如：
[{{"user_id": "候选人ID", "match_score": 95, "reason": "技能匹配度高，具备go和python技能，评分85分，经验丰富"}}]"""
            
            # 调用LLM
            response = await self.call_with_retry(
                user_prompt, 
                system_prompt, 
                settings.default_llm_model
            )
            
            # 解析响应
            try:
                matches = json.loads(response)
                if isinstance(matches, list) and len(matches) > 0:
                    return matches[:3]  # 返回Top-3
                else:
                    logger.warning("LLM returned invalid format, using fallback")
                    return self._fallback_matching(task_requirements, candidates)
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response, using fallback")
                return self._fallback_matching(task_requirements, candidates)
                
        except Exception as e:
            logger.error(f"Error in candidate matching: {str(e)}")
            return self._fallback_matching(task_requirements, candidates)
    
    async def evaluate_submission(self, task_description: str, acceptance_criteria: str, 
                                submission_url: str) -> Tuple[int, List[str]]:
        """评估任务提交"""
        try:
            system_prompt = """你是质量评审助手。根据任务说明、验收标准和提交内容，进行客观评分。

评分标准：
- 90-100分: 完全满足要求，质量优秀
- 80-89分: 基本满足要求，质量良好
- 70-79分: 部分满足要求，需要改进
- 60-69分: 勉强满足要求，问题较多
- 0-59分: 不满足要求，需要重做

请返回JSON格式：{"score": 分数, "failed_reasons": ["问题列表"]}"""
            
            user_prompt = f"""任务说明: {task_description}

验收标准: {acceptance_criteria}

提交链接: {submission_url}

请评估提交内容的质量并给出分数和改进建议。"""
            
            response = await self.call_with_retry(
                user_prompt,
                system_prompt,
                settings.default_llm_model
            )
            
            try:
                result = json.loads(response)
                score = result.get('score', 0)
                failed_reasons = result.get('failed_reasons', [])
                return score, failed_reasons
            except json.JSONDecodeError:
                logger.warning("Failed to parse evaluation response")
                return 60, ["AI评估失败，请人工审核"]
                
        except Exception as e:
            logger.error(f"Error in submission evaluation: {str(e)}")
            return 60, ["AI评估失败，请人工审核"]
    
    def _fallback_matching(self, task_requirements: Dict[str, Any], 
                          candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """降级匹配算法"""
        try:
            required_skills = set(task_requirements.get('skill_tags', []))
            scored_candidates = []
            
            for candidate in candidates:
                candidate_skills = set(candidate.get('skill_tags', []))
                skill_match = len(required_skills & candidate_skills) / len(required_skills) if required_skills else 0
                performance = candidate.get('performance', 0) / 5.0  # 归一化到0-1
                availability = min(candidate.get('hours_available', 0) / 8.0, 1.0)  # 归一化到0-1
                
                # 简单加权评分
                score = int((skill_match * 0.5 + performance * 0.3 + availability * 0.2) * 100)
                
                scored_candidates.append({
                    "user_id": candidate.get('user_id'),
                    "match_score": score,
                    "reason": f"技能匹配{skill_match*100:.0f}%, 历史表现{performance*100:.0f}%"
                })
            
            # 按分数排序并返回Top-3
            scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)
            return scored_candidates[:3]
            
        except Exception as e:
            logger.error(f"Error in fallback matching: {str(e)}")
            return []

# 全局实例
llm_service = LLMService()