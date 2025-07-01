"""
用户登录API实现
TASK123: 实现用户登录功能
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import jwt
import hashlib
import datetime
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user_id: str


class UserService:
    """用户服务类"""
    
    def __init__(self):
        # 模拟用户数据库
        self.users = {
            "admin": {
                "id": "user_001",
                "username": "admin",
                "password_hash": self._hash_password("admin123"),
                "is_active": True
            },
            "developer": {
                "id": "user_002", 
                "username": "developer",
                "password_hash": self._hash_password("dev123"),
                "is_active": True
            }
        }
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_user(self, username: str, password: str) -> Optional[dict]:
        """验证用户凭据"""
        user = self.users.get(username)
        if not user:
            return None
        
        if not user.get("is_active"):
            return None
        
        password_hash = self._hash_password(password)
        if password_hash != user["password_hash"]:
            return None
        
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """根据ID获取用户"""
        for user in self.users.values():
            if user["id"] == user_id:
                return user
        return None


class TokenService:
    """JWT Token服务"""
    
    SECRET_KEY = "your-secret-key-here"
    ALGORITHM = "HS256"
    
    @classmethod
    def create_access_token(cls, user_id: str, expires_delta: int = 3600) -> str:
        """创建访问令牌"""
        expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_delta)
        
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[dict]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# 全局服务实例
user_service = UserService()
token_service = TokenService()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录接口
    
    Args:
        request: 登录请求，包含用户名和密码
        
    Returns:
        LoginResponse: 包含访问令牌的响应
        
    Raises:
        HTTPException: 当用户名或密码错误时
    """
    # 验证用户凭据
    user = user_service.verify_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 创建访问令牌
    access_token = token_service.create_access_token(user["id"])
    
    return LoginResponse(
        access_token=access_token,
        user_id=user["id"]
    )


@router.get("/profile")
async def get_profile(token: str = Depends(security)):
    """
    获取用户信息接口
    
    Args:
        token: Bearer token
        
    Returns:
        dict: 用户信息
        
    Raises:
        HTTPException: 当令牌无效时
    """
    # 验证令牌
    payload = token_service.verify_token(token.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 获取用户信息
    user = user_service.get_user_by_id(payload["user_id"])
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    return {
        "user_id": user["id"],
        "username": user["username"],
        "is_active": user["is_active"]
    }


@router.post("/logout")
async def logout(token: str = Depends(security)):
    """
    用户登出接口
    
    Args:
        token: Bearer token
        
    Returns:
        dict: 登出成功消息
    """
    # 验证令牌（实际项目中可能需要将token加入黑名单）
    payload = token_service.verify_token(token.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="令牌无效",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return {"message": "登出成功"}


# 健康检查
@router.get("/health")
async def auth_health():
    """认证模块健康检查"""
    return {
        "status": "healthy",
        "module": "authentication",
        "timestamp": datetime.datetime.utcnow().isoformat()
    } 