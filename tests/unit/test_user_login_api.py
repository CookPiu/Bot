"""
用户登录API单元测试
TASK123: 实现用户登录功能的测试用例
"""

import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# 模拟导入，实际使用时需要调整路径
try:
    from examples.user_login_api import (
        UserService, TokenService, LoginRequest, 
        router, user_service, token_service
    )
    from fastapi import FastAPI
    
    # 创建测试应用
    app = FastAPI()
    app.include_router(router)
    
except ImportError:
    # 如果无法导入，创建mock对象用于测试结构
    pytest.skip("跳过用户登录API测试 - 模块未找到", allow_module_level=True)


class TestUserService:
    """用户服务测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.user_service = UserService()
    
    def test_hash_password(self):
        """测试密码哈希功能"""
        password = "test123"
        hashed = self.user_service._hash_password(password)
        
        assert hashed is not None
        assert len(hashed) == 64  # SHA256哈希长度
        assert hashed != password  # 确保密码被哈希
    
    def test_verify_user_success(self):
        """测试用户验证成功"""
        user = self.user_service.verify_user("admin", "admin123")
        
        assert user is not None
        assert user["username"] == "admin"
        assert user["id"] == "user_001"
        assert user["is_active"] is True
    
    def test_verify_user_wrong_password(self):
        """测试错误密码"""
        user = self.user_service.verify_user("admin", "wrong_password")
        assert user is None
    
    def test_verify_user_not_found(self):
        """测试用户不存在"""
        user = self.user_service.verify_user("nonexistent", "password")
        assert user is None
    
    def test_get_user_by_id_success(self):
        """测试根据ID获取用户成功"""
        user = self.user_service.get_user_by_id("user_001")
        
        assert user is not None
        assert user["username"] == "admin"
        assert user["id"] == "user_001"
    
    def test_get_user_by_id_not_found(self):
        """测试根据ID获取用户失败"""
        user = self.user_service.get_user_by_id("nonexistent_id")
        assert user is None


class TestTokenService:
    """Token服务测试类"""
    
    def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = "test_user_001"
        token = TokenService.create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_success(self):
        """测试验证令牌成功"""
        user_id = "test_user_001"
        token = TokenService.create_access_token(user_id)
        
        payload = TokenService.verify_token(token)
        
        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["type"] == "access"
    
    def test_verify_token_invalid(self):
        """测试验证无效令牌"""
        invalid_token = "invalid.token.here"
        payload = TokenService.verify_token(invalid_token)
        assert payload is None
    
    def test_verify_token_expired(self):
        """测试验证过期令牌"""
        user_id = "test_user_001"
        
        # 创建已过期的令牌
        expire = datetime.utcnow() - timedelta(seconds=1)
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow() - timedelta(seconds=2),
            "type": "access"
        }
        
        expired_token = jwt.encode(payload, TokenService.SECRET_KEY, algorithm=TokenService.ALGORITHM)
        result = TokenService.verify_token(expired_token)
        assert result is None


class TestLoginAPI:
    """登录API测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)
    
    def test_login_success(self):
        """测试登录成功"""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = self.client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "user_id" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert data["user_id"] == "user_001"
    
    def test_login_wrong_credentials(self):
        """测试登录失败 - 错误凭据"""
        login_data = {
            "username": "admin", 
            "password": "wrong_password"
        }
        
        response = self.client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]
    
    def test_login_missing_fields(self):
        """测试登录失败 - 缺少字段"""
        login_data = {"username": "admin"}
        
        response = self.client.post("/auth/login", json=login_data)
        assert response.status_code == 422  # 验证错误
    
    def test_profile_with_valid_token(self):
        """测试获取用户信息 - 有效令牌"""
        # 先登录获取令牌
        login_data = {"username": "admin", "password": "admin123"}
        login_response = self.client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # 使用令牌获取用户信息
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/auth/profile", headers=headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["user_id"] == "user_001"
        assert data["username"] == "admin"
        assert data["is_active"] is True
    
    def test_profile_with_invalid_token(self):
        """测试获取用户信息 - 无效令牌"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.get("/auth/profile", headers=headers)
        
        assert response.status_code == 401
        assert "令牌无效或已过期" in response.json()["detail"]
    
    def test_profile_without_token(self):
        """测试获取用户信息 - 缺少令牌"""
        response = self.client.get("/auth/profile")
        assert response.status_code == 403  # Forbidden
    
    def test_logout_success(self):
        """测试登出成功"""
        # 先登录获取令牌
        login_data = {"username": "admin", "password": "admin123"}
        login_response = self.client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # 登出
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/auth/logout", headers=headers)
        
        assert response.status_code == 200
        assert response.json()["message"] == "登出成功"
    
    def test_logout_invalid_token(self):
        """测试登出失败 - 无效令牌"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.post("/auth/logout", headers=headers)
        
        assert response.status_code == 401
        assert "令牌无效" in response.json()["detail"]
    
    def test_auth_health_check(self):
        """测试认证模块健康检查"""
        response = self.client.get("/auth/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "authentication"
        assert "timestamp" in data


class TestIntegrationScenarios:
    """集成测试场景"""
    
    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)
    
    def test_complete_user_flow(self):
        """测试完整用户流程"""
        # 1. 登录
        login_data = {"username": "developer", "password": "dev123"}
        login_response = self.client.post("/auth/login", json=login_data)
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 2. 获取用户信息
        headers = {"Authorization": f"Bearer {token}"}
        profile_response = self.client.get("/auth/profile", headers=headers)
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["username"] == "developer"
        
        # 3. 登出
        logout_response = self.client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200
    
    def test_token_reuse_after_logout(self):
        """测试登出后令牌重用（应该仍然有效，因为没有实现黑名单）"""
        # 登录
        login_data = {"username": "admin", "password": "admin123"}
        login_response = self.client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 登出
        logout_response = self.client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        # 尝试再次使用令牌（应该仍然有效，因为没有实现令牌黑名单）
        profile_response = self.client.get("/auth/profile", headers=headers)
        assert profile_response.status_code == 200
    
    @pytest.mark.parametrize("username,password,expected_status", [
        ("admin", "admin123", 200),
        ("developer", "dev123", 200),
        ("admin", "wrong", 401),
        ("nonexistent", "password", 401),
        ("", "password", 422),
        ("username", "", 422),
    ])
    def test_login_various_inputs(self, username, password, expected_status):
        """测试各种登录输入组合"""
        login_data = {"username": username, "password": password}
        response = self.client.post("/auth/login", json=login_data)
        assert response.status_code == expected_status


# 性能测试标记
@pytest.mark.performance
class TestPerformance:
    """性能测试"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_login_performance(self):
        """测试登录性能"""
        import time
        
        login_data = {"username": "admin", "password": "admin123"}
        
        start_time = time.time()
        response = self.client.post("/auth/login", json=login_data)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成
    
    def test_token_verification_performance(self):
        """测试令牌验证性能"""
        import time
        
        # 先获取令牌
        login_data = {"username": "admin", "password": "admin123"}
        login_response = self.client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        start_time = time.time()
        response = self.client.get("/auth/profile", headers=headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 0.5  # 应该在0.5秒内完成 