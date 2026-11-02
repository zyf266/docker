"""忘记密码：手机号（username）+ 阿里云短信验证码。"""
from __future__ import annotations

import logging
import os
import random
import threading
import time
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

_lock = threading.Lock()
# username/phone -> {code, exp, last_sent}
_CODES: Dict[str, Dict[str, Any]] = {}

CODE_TTL_SEC = 600
RESEND_INTERVAL_SEC = 60


def _now() -> float:
    return time.time()


def _cleanup_locked() -> None:
    now = _now()
    dead = [k for k, v in _CODES.items() if float(v.get("exp") or 0) < now]
    for k in dead:
        _CODES.pop(k, None)


def generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def _dev_echo() -> bool:
    return (os.environ.get("PORTAL_PASSWORD_RESET_DEV_ECHO") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _lookup_keys(username: str) -> Set[str]:
    from backpack_quant_trading.core import aliyun_sms

    keys = {(username or "").strip()}
    try:
        keys.add(aliyun_sms.normalize_cn_mobile(username))
    except ValueError:
        pass
    keys.discard("")
    return keys


def send_reset_code(username: str) -> Dict[str, Any]:
    """生成并发送验证码到手机。"""
    from backpack_quant_trading.core import aliyun_sms
    from backpack_quant_trading.database.models import DatabaseManager

    uname = (username or "").strip()
    if len(uname) < 2:
        raise ValueError("请填写手机号")
    mobile = aliyun_sms.normalize_cn_mobile(uname)

    db = DatabaseManager()
    user = db.get_user_by_username(uname) or db.get_user_by_username(mobile)
    if not user:
        raise ValueError("账号不存在")
    store_key = (user.username or mobile).strip()

    with _lock:
        _cleanup_locked()
        prev = _CODES.get(store_key) or _CODES.get(mobile)
        now = _now()
        if prev and now - float(prev.get("last_sent") or 0) < RESEND_INTERVAL_SEC:
            wait = int(RESEND_INTERVAL_SEC - (now - float(prev["last_sent"])))
            raise ValueError(f"发送过于频繁，请 {max(wait, 1)} 秒后再试")
        code = generate_code()
        entry = {"code": code, "exp": now + CODE_TTL_SEC, "last_sent": now}
        _CODES[store_key] = entry
        _CODES[mobile] = entry

    if aliyun_sms.sms_configured():
        ok, detail = aliyun_sms.send_password_reset_code(mobile, code)
        if not ok:
            with _lock:
                _CODES.pop(store_key, None)
                _CODES.pop(mobile, None)
            logger.warning("password reset sms failed phone=%s**** detail=%s", mobile[:3], detail)
            raise ValueError(f"短信发送失败：{detail}")
        deliver_detail = str(detail or "")[:160]
    elif _dev_echo():
        logger.warning("阿里云短信未配置；DEV_ECHO 模式 code=%s phone=%s", code, mobile)
        deliver_detail = "dev_echo"
    else:
        with _lock:
            _CODES.pop(store_key, None)
            _CODES.pop(mobile, None)
        raise ValueError(
            "服务器未配置阿里云短信（ALIYUN_SMS_ACCESS_KEY_ID / SECRET / SIGN_NAME / TEMPLATE_CODE）"
        )

    out: Dict[str, Any] = {
        "ok": True,
        "message": "验证码已发送至手机",
        "delivered": True,
        "ttl_sec": CODE_TTL_SEC,
        "channel": "aliyun_sms",
    }
    if _dev_echo():
        out["dev_code"] = code
        out["deliver_detail"] = deliver_detail
    return out


def verify_and_consume_code(username: str, code: str) -> bool:
    c = (code or "").strip()
    keys = _lookup_keys(username)
    with _lock:
        _cleanup_locked()
        row = None
        for k in keys:
            if k in _CODES:
                row = _CODES[k]
                break
        if not row:
            return False
        if _now() > float(row.get("exp") or 0):
            for k, v in list(_CODES.items()):
                if v is row:
                    _CODES.pop(k, None)
            return False
        if str(row.get("code") or "") != c:
            return False
        for k, v in list(_CODES.items()):
            if v is row or k in keys:
                _CODES.pop(k, None)
        return True


def reset_password(username: str, code: str, new_password: str) -> Dict[str, Any]:
    from backpack_quant_trading.api.deps import get_password_hash
    from backpack_quant_trading.core import aliyun_sms
    from backpack_quant_trading.database.models import DatabaseManager, User

    uname = (username or "").strip()
    if len(new_password or "") < 6:
        raise ValueError("新密码至少 6 位")
    if not verify_and_consume_code(uname, code):
        raise ValueError("验证码无效或已过期")

    try:
        mobile = aliyun_sms.normalize_cn_mobile(uname)
    except ValueError:
        mobile = uname

    db = DatabaseManager()
    session = db.get_session()
    try:
        user = session.query(User).filter(User.username == uname).first()
        if not user and mobile != uname:
            user = session.query(User).filter(User.username == mobile).first()
        if not user:
            raise ValueError("账号不存在")
        user.password_hash = get_password_hash(new_password)
        session.commit()
        return {"ok": True, "username": user.username}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
