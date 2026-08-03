"""实盘实例配置落库（RSA 加密敏感字段）+ 生命周期日志。"""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from backpack_quant_trading.utils.instance_crypto import decrypt_field, encrypt_field
# 确保 Formatter 已切到北京时间
import backpack_quant_trading.utils.logger  # noqa: F401

logger = logging.getLogger(__name__)

_PLAIN_TO_ENC = {
    "private_key": "private_key_enc",
    "api_secret": "api_secret_enc",
    "api_passphrase": "api_passphrase_enc",
}
_PLAIN_KEYS = tuple(_PLAIN_TO_ENC.keys())

_EVENT_LOGGER_NAME = "backpack_quant_trading.instance_events"
_event_logger: Optional[logging.Logger] = None
_ACTION_OK = {
    "start": "启动成功",
    "update": "修改成功",
    "stop": "暂停成功",
}
_ACTION_FAIL = {
    "start": "启动失败",
    "update": "修改失败",
    "stop": "暂停失败",
}


def _default_log_dir() -> Path:
    pkg = Path(__file__).resolve().parents[1]
    # 与 trading.get_logs 一致：优先 package/log，其次 repo/log
    for d in (pkg / "log", pkg.parent / "log"):
        try:
            d.mkdir(parents=True, exist_ok=True)
            return d
        except OSError:
            continue
    return pkg / "log"


def ensure_instance_event_logger(log_dir: Optional[Path] = None) -> logging.Logger:
    """初始化 strategy_instances.log（幂等）。"""
    global _event_logger
    if _event_logger is not None:
        return _event_logger
    log_dir = log_dir or _default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "strategy_instances.log"
    lg = logging.getLogger(_EVENT_LOGGER_NAME)
    lg.setLevel(logging.INFO)
    lg.propagate = False
    if not any(isinstance(h, RotatingFileHandler) for h in lg.handlers):
        fh = RotatingFileHandler(
            path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        lg.addHandler(fh)
    _event_logger = lg
    return lg


def write_instance_event(
    action: str,
    instance_id: str,
    ok: bool = True,
    detail: str = "",
) -> None:
    """写入实例生命周期事件。action: start|update|stop"""
    lg = ensure_instance_event_logger()
    label = (_ACTION_OK if ok else _ACTION_FAIL).get(action, action)
    extra = f" | {detail}" if detail else ""
    msg = f"{label} | instance_id={instance_id}{extra}"
    if ok:
        lg.info(msg)
    else:
        lg.error(msg)


def strip_secrets_for_api(obj: Optional[dict]) -> Optional[dict]:
    """列表/API 回显：去掉明文与密文字段。"""
    if not isinstance(obj, dict):
        return obj
    out = dict(obj)
    for plain, enc in _PLAIN_TO_ENC.items():
        out.pop(plain, None)
        out.pop(enc, None)
    return out


def sanitize_and_encrypt_config(
    obj: Dict[str, Any],
    secrets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """合并配置：新明文密钥加密写入 *_enc；始终删除明文密钥字段。"""
    out = dict(obj or {})
    secrets = secrets or {}
    for plain, enc in _PLAIN_TO_ENC.items():
        val = secrets.get(plain)
        if val is None or str(val).strip() == "":
            # 请求未带新密钥：保留已有 *_enc，删除可能混入的明文
            out.pop(plain, None)
            continue
        out[enc] = encrypt_field(str(val).strip())
        out.pop(plain, None)
    # 防御：任何残留明文一律剔除
    for plain in _PLAIN_KEYS:
        out.pop(plain, None)
    return out


def load_secrets_from_config(obj: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """从 *_enc 解密得到明文密钥字典。"""
    result: Dict[str, str] = {}
    if not isinstance(obj, dict):
        return result
    for plain, enc in _PLAIN_TO_ENC.items():
        ct = obj.get(enc)
        if not ct:
            continue
        try:
            result[plain] = decrypt_field(str(ct))
        except Exception as exc:
            logger.error("解密 %s 失败 instance 字段损坏: %s", enc, exc)
            raise
    return result


def persist_live_config(
    db,
    user_id: int,
    instance_id: str,
    obj: Dict[str, Any],
    secrets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """加密敏感字段后写入 user_instances。磁盘过满时提前失败，避免 MySQL COMMIT 挂死。"""
    try:
        import shutil

        usage = shutil.disk_usage("/")
        free_mb = usage.free / (1024 * 1024)
        if free_mb < 300:
            raise RuntimeError(
                f"服务器磁盘空间不足（剩余 {free_mb:.0f}MB），请清理后再启动策略"
            )
    except RuntimeError:
        raise
    except Exception:
        pass
    cleaned = sanitize_and_encrypt_config(obj, secrets)
    db.save_user_instance(
        user_id, "live", instance_id, json.dumps(cleaned, ensure_ascii=False)
    )
    return cleaned
