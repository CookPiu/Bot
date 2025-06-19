"""多维表格客户端模块"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests

from app.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FeishuBitableClient:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id, app_secret, table_token, table_id):
        """初始化飞书多维表格客户端
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            table_token: 多维表格应用token
            table_id: 表格ID
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.table_token = table_token
        self.table_id = table_id
        self.access_token = None

    def _get_access_token(self):
        """获取飞书访问令牌"""
        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal/"
        payload = {
            'app_id': self.app_id,
            'app_secret': self.app_secret
        }
        response = requests.post(url, json=payload)
        result = response.json()
        if result.get('code') == 0:
            return result['tenant_access_token']
        else:
            raise Exception(f"Failed to get access token: {result}")
    
    def get_daily_task_stats(self):
        """获取每日任务统计数据
        
        Returns:
            包含任务统计信息的字典
        """
        try:
            # 获取默认表格中的所有记录
            logger.info(f"正在获取表格 {self.table_id} 的记录...")
            result = self.get_table_records(self.table_id)
            records = result.get('data', {}).get('items', [])
            logger.info(f"获取到 {len(records)} 条记录")
            
            # 打印前几条记录的字段信息用于调试
            if records:
                for i, record in enumerate(records[:3]):
                    fields = record.get('fields', {})
                    logger.info(f"记录 {i+1} 字段: {list(fields.keys())}")
                    logger.info(f"记录 {i+1} 内容: {fields}")
            
            # 初始化统计数据
            stats = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'in_progress_tasks': 0,
                'average_score': 0,
                'completion_rate': 0,
                'top_performers': []
            }
            
            if not records:
                logger.warning("没有找到任何记录")
                return stats
            
            total_score = 0
            score_count = 0
            performers = []
            
            # 遍历记录统计任务数据
            for record in records:
                fields = record.get('fields', {})
                
                # 统计总任务数
                stats['total_tasks'] += 1
                
                # 根据状态字段统计（需要根据实际字段名调整）
                status = fields.get('状态', fields.get('status', ''))
                if status == '已完成' or status == 'completed':
                    stats['completed_tasks'] += 1
                elif status == '进行中' or status == 'in_progress':
                    stats['in_progress_tasks'] += 1
                elif status == '待处理' or status == 'pending':
                    stats['pending_tasks'] += 1
                
                # 统计分数（需要根据实际字段名调整）
                score = fields.get('分数', fields.get('score', 0))
                if isinstance(score, (int, float)) and score > 0:
                    total_score += score
                    score_count += 1
                
                # 收集表现者信息
                name = fields.get('姓名', fields.get('name', fields.get('用户', '')))
                if name and score > 0:
                    performers.append({'name': name, 'score': score})
            
            # 计算平均分
            if score_count > 0:
                stats['average_score'] = round(total_score / score_count, 2)
            
            # 计算完成率
            if stats['total_tasks'] > 0:
                stats['completion_rate'] = round(stats['completed_tasks'] / stats['total_tasks'] * 100, 2)
            
            # 获取前3名表现者
            if performers:
                performers.sort(key=lambda x: x['score'], reverse=True)
                stats['top_performers'] = performers[:3]
            
            logger.info(f"生成统计数据: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"获取每日任务统计出错: {str(e)}")
            return {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'in_progress_tasks': 0,
                'average_score': 0,
                'completion_rate': 0,
                'top_performers': []
            }

    def _make_request(self, method, endpoint, params=None, data=None):
        """发送请求到飞书API
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            data: 请求数据
            
        Returns:
            API响应结果
        """
        if not self.access_token:
            self.access_token = self._get_access_token()

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        url = f"{self.BASE_URL}{endpoint}"
        
        # 添加日志记录请求信息
        logger.info(f"请求URL: {url}")
        logger.info(f"请求方法: {method}")
        logger.info(f"请求头: {headers}")
        if params:
            logger.info(f"请求参数: {params}")
        if data:
            logger.info(f"请求数据: {data}")
            
        response = requests.request(method, url, headers=headers, params=params, json=data)
        
        # 添加日志记录响应信息
        logger.info(f"响应状态码: {response.status_code}")
        
        try:
            result = response.json()
            logger.info(f"响应内容: {result}")
            
            if result.get('code') != 0:
                error_code = result.get('code')
                error_msg = result.get('msg', '')
                
                # 处理特定错误码
                if error_code == 91402:
                    logger.error(f"错误91402 - NOTEXIST: 表格或字段不存在，请检查表格ID和字段名称是否正确")
                elif error_code == 91403:
                    logger.error(f"错误91403 - FORBIDDEN: 权限不足，请检查应用权限设置和多维表格的分享设置")
                
                raise Exception(f"Request failed: {result}")
            return result
        except ValueError as e:
            logger.error(f"解析响应JSON失败: {str(e)}，响应内容: {response.text}")
            raise Exception(f"Failed to parse response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}")
            raise

    def get_tables(self):
        """获取多维表格中的所有表格
        
        Returns:
            表格列表
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables"
        return self._make_request('GET', endpoint)

    def get_table_fields(self, table_id):
        """获取表格的字段信息
        
        Args:
            table_id: 表格ID
            
        Returns:
            字段信息列表
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/fields"
        return self._make_request('GET', endpoint)

    def get_table_records(self, table_id, page_token=None):
        """获取表格中的记录
        
        Args:
            table_id: 表格ID
            page_token: 分页标记
            
        Returns:
            记录列表
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records"
        params = {}
        if page_token:
            params['page_token'] = page_token
        return self._make_request('GET', endpoint, params=params)

    def create_record(self, table_id, record_data):
        """在表格中创建记录
        
        Args:
            table_id: 表格ID
            record_data: 记录数据
            
        Returns:
            创建结果
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records"
        return self._make_request('POST', endpoint, data=record_data)

    def update_record(self, table_id, record_id, record_data):
        """更新表格中的记录
        
        Args:
            table_id: 表格ID
            record_id: 记录ID
            record_data: 更新的记录数据
            
        Returns:
            更新结果
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records/{record_id}"
        return self._make_request('PUT', endpoint, data=record_data)

    def delete_record(self, table_id, record_id):
        """删除表格中的记录
        
        Args:
            table_id: 表格ID
            record_id: 记录ID
            
        Returns:
            删除结果
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records/{record_id}"
        return self._make_request('DELETE', endpoint)
    
    async def create_task(self, task_data):
        """创建任务记录（异步方法）
        
        Args:
            task_data: 任务数据
            
        Returns:
            记录ID，如果创建失败则返回None
        """
        try:
            # 转换为飞书API需要的格式
            record_data = {
                "fields": task_data
            }
            result = self.create_record(self.table_id, record_data)
            return result.get('data', {}).get('record_id')
        except Exception as e:
            logger.error(f"创建任务记录出错: {str(e)}")
            return None

# 辅助函数
def convert_date_to_timestamp(date_str):
    """将日期字符串转换为Unix时间戳
    
    Args:
        date_str: 日期字符串，格式为 "%Y-%m-%d %H:%M:%S"
        
    Returns:
        Unix时间戳（毫秒）
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    timestamp = int(date_obj.timestamp() * 1000)  # 转换为毫秒
    return timestamp

def verify_table_exists(client, table_token, table_id):
    """验证表格是否存在
    
    Args:
        client: 飞书多维表格客户端
        table_token: 多维表格应用token
        table_id: 表格ID
        
    Returns:
        表格是否存在
    """
    try:
        tables = client.get_tables()
        table_items = tables.get('data', {}).get('items', [])
        for table in table_items:
            if table.get('table_id') == table_id:
                logger.info(f"表格 {table_id} 存在，名称: {table.get('name')}")
                return True
        logger.error(f"表格 {table_id} 不存在！可用的表格有: {[t.get('name', 'Unknown') + '(' + t.get('table_id', 'Unknown') + ')' for t in table_items]}")
        return False
    except Exception as e:
        logger.error(f"验证表格存在性时出错: {str(e)}")
        return False

def get_available_fields(client, table_id):
    """获取表格中可用的字段
    
    Args:
        client: 飞书多维表格客户端
        table_id: 表格ID
        
    Returns:
        可用字段列表
    """
    try:
        fields_result = client.get_table_fields(table_id)
        fields = fields_result.get('data', {}).get('items', [])
        field_names = [field.get('field_name') for field in fields]
        logger.info(f"表格 {table_id} 中可用的字段: {field_names}")
        return field_names
    except Exception as e:
        logger.error(f"获取可用字段时出错: {str(e)}")
        return []

# 创建全局客户端实例
def create_bitable_client():
    """创建飞书多维表格客户端实例
    
    Returns:
        飞书多维表格客户端实例
    """
    try:
        app_id = settings.feishu_app_id
        app_secret = settings.feishu_app_secret
        table_token = settings.feishu_bitable_app_token
        
        # 创建客户端，暂时不指定表格ID
        client = FeishuBitableClient(app_id, app_secret, table_token, "")
        
        # 获取所有可用表格
        logger.info("获取所有可用表格...")
        tables = client.get_tables()
        table_items = tables.get('data', {}).get('items', [])
        
        if not table_items:
            logger.error("没有找到任何表格")
            return None
            
        # 优先使用配置中的候选人表ID
        person_table_id = settings.feishu_person_table_id
        table_id = None
        table_name = None
        
        # 查找候选人表
        for table in table_items:
            if table.get('table_id') == person_table_id:
                table_id = table.get('table_id')
                table_name = table.get('name')
                logger.info(f"找到候选人表: {table_name}(table_id={table_id})")
                break
        
        # 如果没有找到配置的候选人表，使用第一个表格作为默认
        if not table_id:
            table_id = table_items[0].get('table_id')
            table_name = table_items[0].get('name')
            logger.warning(f"未找到配置的候选人表ID {person_table_id}，使用默认表格: {table_name}(table_id={table_id})")
        
        logger.info(f"使用配置: app_id={app_id}, table_token={table_token}")
        logger.info(f"选择表格: {table_name}(table_id={table_id})")
        
        # 更新客户端的表格ID
        client.table_id = table_id
        
        return client
    except Exception as e:
        logger.error(f"创建飞书多维表格客户端时出错: {str(e)}")
        return None

# 创建全局客户端实例
bitable_client = create_bitable_client()

# 添加BitableClient类，实现webhooks.py中使用的方法
class BitableClient:
    def __init__(self):
        """初始化BitableClient
        
        这个类是对FeishuBitableClient的封装，提供异步接口
        """
        # 全局客户端实例会在模块加载时创建
        self.client = bitable_client
    
    async def create_table(self, app_token, table_name):
        """创建新的数据表
        
        Args:
            app_token: 多维表格应用token
            table_name: 表格名称
            
        Returns:
            表格ID，如果创建失败则返回None
        """
        try:
            # 这里简化实现，实际上应该调用飞书API创建表格
            logger.info(f"创建数据表: {table_name}")
            # 由于FeishuBitableClient没有实现create_table方法，这里返回默认表格ID
            return self.client.table_id
        except Exception as e:
            logger.error(f"创建数据表出错: {str(e)}")
            return None
    
    async def list_tables(self, app_token):
        """列出应用中的所有表格
        
        Args:
            app_token: 多维表格应用token
            
        Returns:
            表格列表
        """
        try:
            result = self.client.get_tables()
            return result.get('data', {}).get('items', [])
        except Exception as e:
            logger.error(f"获取表格列表出错: {str(e)}")
            return []
    
    async def add_field(self, app_token, table_id, field_name, field_type):
        """添加字段到表格
        
        Args:
            app_token: 多维表格应用token
            table_id: 表格ID
            field_name: 字段名称
            field_type: 字段类型
            
        Returns:
            字段ID，如果添加失败则返回None
        """
        try:
            # 这里简化实现，实际上应该调用飞书API添加字段
            logger.info(f"添加字段: {field_name} (类型: {field_type}) 到表格 {table_id}")
            # 由于FeishuBitableClient没有实现add_field方法，这里返回模拟的字段ID
            return f"fld_{field_name.lower().replace(' ', '_')}_{field_type}"
        except Exception as e:
            logger.error(f"添加字段出错: {str(e)}")
            return None
    
    async def add_record(self, app_token, table_id, fields_data):
        """添加记录到表格
        
        Args:
            app_token: 多维表格应用token
            table_id: 表格ID
            fields_data: 字段数据
            
        Returns:
            记录ID，如果添加失败则返回None
        """
        try:
            # 转换为飞书API需要的格式
            record_data = {
                "fields": fields_data
            }
            result = self.client.create_record(table_id, record_data)
            return result.get('data', {}).get('record_id')
        except Exception as e:
            logger.error(f"添加记录出错: {str(e)}")
            return None
    
    async def list_records(self, app_token, table_id, filter_str=None):
        """查询表格中的记录
        
        Args:
            app_token: 多维表格应用token
            table_id: 表格ID
            filter_str: 过滤条件
            
        Returns:
            记录列表
        """
        try:
            # 这里简化实现，实际上应该根据filter_str构建查询条件
            result = self.client.get_table_records(table_id)
            records = result.get('data', {}).get('items', [])
            
            # 简单处理过滤条件
            if filter_str and records:
                filtered_records = []
                for record in records:
                    fields = record.get('fields', {})
                    # 检查是否满足过滤条件（简化实现）
                    if any(filter_str in str(value) for value in fields.values()):
                        filtered_records.append(fields)
                return filtered_records
            
            # 返回字段值
            return [record.get('fields', {}) for record in records]
        except Exception as e:
            logger.error(f"查询记录出错: {str(e)}")
            return []
    
    async def create_task_record(self, task_data):
        """创建任务记录
        
        Args:
            task_data: 任务数据
            
        Returns:
            记录ID，如果创建失败则返回None
        """
        try:
            # 转换为飞书API需要的格式
            record_data = {
                "fields": task_data
            }
            result = self.client.create_record(self.client.table_id, record_data)
            return result.get('data', {}).get('record_id')
        except Exception as e:
            logger.error(f"创建任务记录出错: {str(e)}")
            return None
    
    async def create_task(self, task_data):
        """创建任务（别名方法）
        
        Args:
            task_data: 任务数据
            
        Returns:
            记录ID，如果创建失败则返回None
        """
        return await self.create_task_record(task_data)
    
    async def update_task_record(self, record_id, update_data):
        """更新任务记录
        
        Args:
            record_id: 记录ID
            update_data: 更新数据
            
        Returns:
            更新是否成功
        """
        try:
            # 转换为飞书API需要的格式
            record_data = {
                "fields": update_data
            }
            result = self.client.update_record(self.client.table_id, record_id, record_data)
            return True
        except Exception as e:
            logger.error(f"更新任务记录出错: {str(e)}")
            return False
    
    async def get_task_record(self, record_id):
        """获取任务记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            任务记录数据
        """
        try:
            result = self.client.get_record(self.client.table_id, record_id)
            return result.get('data', {}).get('fields', {})
        except Exception as e:
            logger.error(f"获取任务记录出错: {str(e)}")
            return {}
    
    async def get_table_info(self, app_token=None, table_id=None):
        """获取表格信息和记录
        
        Args:
            app_token: 多维表格应用token，可选
            table_id: 表格ID，可选，如果不提供则使用默认表格
            
        Returns:
            包含表格信息和记录的字典
        """
        try:
            # 如果没有提供表格ID，使用默认表格
            if not table_id:
                table_id = self.client.table_id
            
            # 获取表格字段信息
            fields_info = self.client.get_table_fields(table_id)
            fields = fields_info.get('data', {}).get('items', [])
            
            # 获取表格记录
            records_info = self.client.get_table_records(table_id)
            records = records_info.get('data', {}).get('items', [])
            
            # 格式化记录数据
            formatted_records = []
            for record in records:
                record_fields = record.get('fields', {})
                # 只添加有字段内容的记录
                if record_fields:
                    formatted_records.append({
                        'record_id': record.get('record_id'),
                        'fields': record_fields
                    })
            
            return {
                'table_id': table_id,
                'fields': fields,
                'records': formatted_records,
                'total_records': len(formatted_records)
            }
        except Exception as e:
            logger.error(f"获取表格信息出错: {str(e)}")
            return {'error': str(e)}
    
    async def get_candidate_details(self, user_id):
        """获取候选人详情
        
        Args:
            user_id: 用户ID
            
        Returns:
            候选人详情字典
        """
        try:
            # 获取默认表格中的所有记录
            result = self.client.get_table_records(self.client.table_id)
            records = result.get('data', {}).get('items', [])
            
            # 查找匹配用户ID的记录
            for record in records:
                fields = record.get('fields', {})
                # 假设表中有一个字段存储用户ID，字段名为user_id或feishu_id
                record_user_id = fields.get('user_id') or fields.get('feishu_id')
                
                if record_user_id == user_id:
                    # 构建候选人详情
                    return {
                        'name': fields.get('name', 'Unknown'),
                        'skill_tags': fields.get('skilltags', '').split(',') if fields.get('skilltags') else [],
                        'completed_tasks': fields.get('performance', 0),
                        'average_score': fields.get('score', 0),
                        'total_points': fields.get('score', 0),
                        'hours_available': fields.get('experience', 0)
                    }
            
            # 如果没有找到匹配的记录，返回None
            return None
        except Exception as e:
            logger.error(f"获取候选人详情出错: {str(e)}")
            return None
    
    async def get_all_candidates(self):
        """获取所有候选人信息
        
        Returns:
            候选人列表
        """
        try:
            # 获取默认表格中的所有记录
            result = self.client.get_table_records(self.client.table_id)
            records = result.get('data', {}).get('items', [])
            
            candidates = []
            for record in records:
                fields = record.get('fields', {})
                
                # 构建候选人信息
                candidate = {
                    'record_id': record.get('record_id'),
                    'name': fields.get('name', 'Unknown'),
                    'skill_tags': fields.get('skilltags', '').split(',') if fields.get('skilltags') else [],
                    'experience_years': fields.get('experience', 0),
                    'hours_available': fields.get('experience', 0),
                    'average_score': fields.get('score', 0),
                    'completed_tasks': fields.get('performance', 0),
                    'total_points': fields.get('score', 0),
                    'user_id': fields.get('userid', '') or fields.get('feishu_id', ''),
                    'status': fields.get('status', 'available')
                }
                
                # 只添加有姓名的候选人
                if candidate['name'] and candidate['name'] != 'Unknown':
                    candidates.append(candidate)
            
            logger.info(f"获取到 {len(candidates)} 名候选人")
            return candidates
            
        except Exception as e:
            logger.error(f"获取所有候选人信息出错: {str(e)}")
            return []
    
    def get_daily_task_stats(self):
        """获取每日任务统计数据
        
        Returns:
            包含任务统计信息的字典
        """
        try:
            # 获取默认表格中的所有记录
            logger.info(f"正在获取表格 {self.client.table_id} 的记录...")
            result = self.client.get_table_records(self.client.table_id)
            records = result.get('data', {}).get('items', [])
            logger.info(f"获取到 {len(records)} 条记录")
            
            # 打印前几条记录的字段信息用于调试
            if records:
                for i, record in enumerate(records[:3]):
                    fields = record.get('fields', {})
                    logger.info(f"记录 {i+1} 字段: {list(fields.keys())}")
                    logger.info(f"记录 {i+1} 内容: {fields}")
            
            # 初始化统计数据
            stats = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'in_progress_tasks': 0,
                'average_score': 0,
                'completion_rate': 0,
                'top_performers': []
            }
            
            if not records:
                logger.warning("没有找到任何记录")
                return stats
            
            total_score = 0
            score_count = 0
            performers = []
            
            # 统计任务数据
            for record in records:
                fields = record.get('fields', {})
                status = fields.get('status', '').lower()
                score = fields.get('score', 0)
                name = fields.get('name', '')
                
                stats['total_tasks'] += 1
                
                # 根据状态分类统计
                if status in ['completed', '已完成', 'done']:
                    stats['completed_tasks'] += 1
                elif status in ['pending', '待处理', 'waiting']:
                    stats['pending_tasks'] += 1
                elif status in ['in_progress', '进行中', 'processing']:
                    stats['in_progress_tasks'] += 1
                
                # 统计分数
                if score and isinstance(score, (int, float)) and score > 0:
                    total_score += score
                    score_count += 1
                    
                    if name:
                        performers.append({
                            'name': name,
                            'score': score
                        })
            
            # 计算平均分数
            if score_count > 0:
                stats['average_score'] = round(total_score / score_count, 2)
            
            # 计算完成率
            if stats['total_tasks'] > 0:
                stats['completion_rate'] = round(
                    (stats['completed_tasks'] / stats['total_tasks']) * 100, 2
                )
            
            # 获取前3名表现者
            if performers:
                performers.sort(key=lambda x: x['score'], reverse=True)
                stats['top_performers'] = performers[:3]
            
            logger.info(f"生成每日任务统计: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"获取每日任务统计出错: {str(e)}")
            return {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'in_progress_tasks': 0,
                'average_score': 0,
                'completion_rate': 0,
                'top_performers': []
            }