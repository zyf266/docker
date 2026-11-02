"""认证 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backpack_quant_trading.database.models import DatabaseManager
from backpack_quant_trading.api.deps import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    require_user,
)
from backpack_quant_trading.core import portal_password_reset as pw_reset

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str


class ForgotSendCodeIn(BaseModel):
    username: str = Field(..., description="手机号/登录账号")


class ForgotResetIn(BaseModel):
    username: str
    code: str
    new_password: str


@router.post("/login")
def login(req: LoginRequest):
    db = DatabaseManager()
    user = db.get_user_by_username(req.username)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }


@router.post("/register")
def register(req: RegisterRequest):
    """页面自主注册一律为普通用户；管理员只能用云端 CLI 创建。"""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(req.username.strip()) < 2:
        raise HTTPException(status_code=400, detail="用户名至少 2 个字符")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    db = DatabaseManager()
    if db.get_user_by_username(req.username.strip()):
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = db.create_user(req.username.strip(), get_password_hash(req.password), role="user")
    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }


@router.post("/forgot-password/send-code")
def forgot_send_code(body: ForgotSendCodeIn):
    try:
        return pw_reset.send_reset_code(body.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送验证码失败: {e}") from e


@router.post("/forgot-password/reset")
def forgot_reset(body: ForgotResetIn):
    try:
        return pw_reset.reset_password(body.username, body.code, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置密码失败: {e}") from e


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(require_user)):
    return user


@router.post("/logout")
def logout():
    return {"message": "ok"}
