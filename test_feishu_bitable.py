import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

# 导入用户提供的FeishuBitableClient类
from datetime import datetime
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FeishuBitableClient:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id, app_secret, table_token, table_id):
        self.app_id = "cli_a8d880f40cf8100c"
        self.app_secret = "dCDrxGDi8bHgSr5o5G5fvdTWfubKIDfL"
        self.table_token = "SNoBbdo2yaaljXsqLaTc4X7tnff"
        self.table_id = "tblZywtnvmkLqWPK"
        self.access_token = None

    def _get_access_token(self):
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

    def _make_request(self, method, endpoint, params=None, data=None):
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
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables"
        return self._make_request('GET', endpoint)

    def get_table_fields(self, table_id):
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/fields"
        return self._make_request('GET', endpoint)

    def get_table_records(self, table_id, page_token=None):
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records"
        params = {}
        if page_token:
            params['page_token'] = page_token
        return self._make_request('GET', endpoint, params=params)

    def create_record(self, table_id, record_data):
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records"
        return self._make_request('POST', endpoint, data=record_data)

    def update_record(self, table_id, record_id, record_data):
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records/{record_id}"
        return self._make_request('PUT', endpoint, data=record_data)

    def delete_record(self, table_id, record_id):
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records/{record_id}"
        return self._make_request('DELETE', endpoint)

def convert_date_to_timestamp(date_str):
    """
    将日期字符串转换为Unix时间戳
    :param date_str: 日期字符串，格式为 "%Y-%m-%d %H:%M:%S"
    :return: Unix时间戳
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    timestamp = int(date_obj.timestamp() * 1000)  # 转换为毫秒
    return timestamp

def update_record_with_timestamp(record_data):
    """
    更新记录数据中的日期字段为Unix时间戳
    """
    if "账单日" in record_data["fields"]:
        date_str = record_data["fields"]["账单日"]
        timestamp = convert_date_to_timestamp(date_str)
        record_data["fields"]["账单日"] = timestamp
    return record_data

def verify_table_exists(client, table_token, table_id):
    """
    验证表格是否存在
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
    """
    获取表格中可用的字段
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

def test_task_table():
    """
    测试任务表的基本操作
    """
    try:
        # 使用项目配置中的凭据
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
            logger.error("没有找到任何表格，终止测试")
            return
            
        # 使用第一个表格作为测试表格
        table_id = table_items[0].get('table_id')
        table_name = table_items[0].get('name')
        
        logger.info(f"使用配置: app_id={app_id}, table_token={table_token}")
        logger.info(f"选择表格: {table_name}(table_id={table_id})")
        
        # 更新客户端的表格ID
        client.table_id = table_id
        
        # 1. 验证表格是否存在
        logger.info("验证表格是否存在...")
        if not verify_table_exists(client, table_token, table_id):
            logger.error("表格不存在，终止测试")
            return

        # 2. 获取字段信息
        logger.info(f"获取表格 {table_id} 的字段信息...")
        available_fields = get_available_fields(client, table_id)
        if not available_fields:
            logger.error("无法获取字段信息，终止测试")
            return

        # 3. 创建一条测试记录，只使用存在的字段
        logger.info("创建测试记录...")
        test_record = {"fields": {}}
        
        # 根据实际可用字段构建记录
        field_mapping = {
            "任务标题": "测试任务",
            "任务描述": "这是一个通过API创建的测试任务",
            "技能标签": ["Python", "API测试"],
            "截止时间": datetime.now().isoformat(),
            "状态": "pending",
            "紧急程度": "normal",
            "预估工时": 2,
            "奖励积分": 50,
            "创建者": "测试脚本",
            "创建时间": datetime.now().isoformat(),
            "任务ID": f"TEST-{int(datetime.now().timestamp())}"
        }
        
        # 只添加表格中存在的字段
        for field, value in field_mapping.items():
            if field in available_fields:
                test_record["fields"][field] = value
            else:
                logger.warning(f"字段 '{field}' 在表格中不存在，跳过")
        
        if not test_record["fields"]:
            logger.error("没有可用的匹配字段，无法创建记录")
            return
            
        logger.info(f"将要创建的记录: {test_record}")
        
        try:
            create_result = client.create_record(table_id, test_record)
            logger.info(f"创建记录结果: {create_result}")
            record_id = create_result.get("data", {}).get("record", {}).get("record_id")

            if record_id:
                # 4. 更新记录
                logger.info(f"更新记录 {record_id}...")
                updated_record = {"fields": {}}
                
                # 只更新存在的字段
                update_mapping = {
                    "任务标题": "已更新的测试任务",
                    "状态": "in_progress",
                    "紧急程度": "high"
                }
                
                for field, value in update_mapping.items():
                    if field in available_fields:
                        updated_record["fields"][field] = value
                
                if updated_record["fields"]:
                    update_result = client.update_record(table_id, record_id, updated_record)
                    logger.info(f"更新记录结果: {update_result}")
                else:
                    logger.warning("没有可更新的字段，跳过更新操作")

                # 5. 获取记录
                logger.info("获取所有记录...")
                records = client.get_table_records(table_id)
                logger.info(f"获取到 {len(records.get('data', {}).get('items', []))} 条记录")

                # 6. 删除记录
                logger.info(f"删除记录 {record_id}...")
                delete_result = client.delete_record(table_id, record_id)
                logger.info(f"删除记录结果: {delete_result}")
            else:
                logger.error("创建记录失败，无法获取记录ID")
        except Exception as e:
            logger.error(f"操作记录时出错: {str(e)}")

    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def test_with_timestamp():
    """
    测试带有时间戳转换的记录操作
    """
    try:
        # 使用项目配置中的凭据
        app_id = settings.feishu_app_id
        app_secret = settings.feishu_app_secret
        table_token = settings.feishu_bitable_app_token
        
        # 创建客户端，暂时不指定表格ID
        client = FeishuBitableClient(app_id, app_secret, table_token, "")
        
        # 获取所有可用表格
        logger.info("时间戳测试：获取所有可用表格...")
        tables = client.get_tables()
        table_items = tables.get('data', {}).get('items', [])
        
        if not table_items:
            logger.error("没有找到任何表格，终止时间戳测试")
            return
            
        # 使用第一个表格作为测试表格
        table_id = table_items[0].get('table_id')
        table_name = table_items[0].get('name')
        
        logger.info(f"时间戳测试使用配置: app_id={app_id}, table_token={table_token}")
        logger.info(f"时间戳测试选择表格: {table_name}(table_id={table_id})")
        
        # 更新客户端的表格ID
        client.table_id = table_id
        
        # 验证表格是否存在
        if not verify_table_exists(client, table_token, table_id):
            logger.error("表格不存在，终止时间戳测试")
            return
            
        # 获取可用字段
        available_fields = get_available_fields(client, table_id)
        
        # 检查是否有日期类型字段可用于测试
        date_field = None
        if "账单日" in available_fields:
            date_field = "账单日"
        elif "截止时间" in available_fields:
            date_field = "截止时间"
        elif "创建时间" in available_fields:
            date_field = "创建时间"
        
        if not date_field:
            logger.warning("没有找到可用的日期字段进行时间戳测试，将创建一个基本记录")
            # 创建一个基本记录，不包含日期字段
            record_data = {"fields": {}}
            
            # 添加一些基本字段
            for field in ["任务标题", "任务描述"]:
                if field in available_fields:
                    record_data["fields"][field] = f"时间戳测试 - {field}"
        else:
            # 创建带有日期字段的记录
            record_data = {
                "fields": {
                    "任务标题": "时间戳测试" if "任务标题" in available_fields else None,
                    "任务描述": "测试时间戳转换功能" if "任务描述" in available_fields else None,
                    date_field: "2024-10-10 00:00:00"  # 使用找到的日期字段
                }
            }
            
            # 移除值为None的字段
            record_data["fields"] = {k: v for k, v in record_data["fields"].items() if v is not None}
            
            # 转换时间戳
            if date_field == "账单日":  # 只有账单日字段需要转换
                record_data = update_record_with_timestamp(record_data)
                logger.info(f"转换后的记录数据: {record_data}")
        
        if not record_data["fields"]:
            logger.error("没有可用字段创建记录，终止时间戳测试")
            return
            
        # 尝试创建记录
        try:
            logger.info(f"将要创建的记录: {record_data}")
            create_result = client.create_record(table_id, record_data)
            logger.info(f"创建记录结果: {create_result}")
            
            # 如果创建成功，尝试删除记录以清理
            record_id = create_result.get("data", {}).get("record", {}).get("record_id")
            if record_id:
                logger.info(f"清理测试记录 {record_id}...")
                delete_result = client.delete_record(table_id, record_id)
                logger.info(f"删除记录结果: {delete_result}")
        except Exception as e:
            logger.warning(f"创建记录失败: {str(e)}")

    except Exception as e:
        logger.error(f"时间戳测试过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    """
    主函数
    """
    logger.info("开始测试飞书多维表格API...")
    
    # 测试任务表操作
    test_task_table()
    
    # 测试时间戳转换功能
    test_with_timestamp()
    
    logger.info("测试完成")

if __name__ == "__main__":
    main()