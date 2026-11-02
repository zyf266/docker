"""阿里云短信（Dysmsapi SendSms），仅依赖 requests。"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

ENDPOINT = "https://dysmsapi.aliyuncs.com/"


def _cfg(name: str, *alts: str) -> str:
    for key in (name, *alts):
        v = (os.environ.get(key) or "").strip()
        if v:
            return v
    return ""


def sms_configured() -> bool:
    return bool(
        _cfg("ALIYUN_SMS_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_ID")
        and _cfg("ALIYUN_SMS_ACCESS_KEY_SECRET", "ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        and _cfg("ALIYUN_SMS_SIGN_NAME")
        and _cfg("ALIYUN_SMS_TEMPLATE_CODE", "ALIYUN_SMS_TEMPLATE_CODE_RESET")
    )


def normalize_cn_mobile(phone: str) -> str:
    """收成 11 位国内手机号；非法则抛 ValueError。"""
    s = (phone or "").strip().replace(" ", "").replace("-", "")
    if s.startswith("+86"):
        s = s[3:]
    elif s.startswith("0086"):
        s = s[4:]
    if s.startswith("86") and len(s) == 13:
        s = s[2:]
    if not (len(s) == 11 and s.isdigit() and s.startswith("1")):
        raise ValueError("请填写有效的中国大陆手机号（11 位）")
    return s


def _percent_encode(s: str) -> str:
    return quote(str(s), safe="~")


def _sign(secret: str, string_to_sign: str) -> str:
    import base64

    key = (secret + "&").encode("utf-8")
    dig = hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(dig).decode("utf-8")


def send_sms(
    phone: str,
    *,
    template_param: Dict[str, Any],
    sign_name: Optional[str] = None,
    template_code: Optional[str] = None,
    timeout: float = 12.0,
) -> Tuple[bool, str]:
    """发送短信。成功返回 (True, BizId/OK)；失败 (False, 原因)。"""
    ak = _cfg("ALIYUN_SMS_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_ID")
    sk = _cfg("ALIYUN_SMS_ACCESS_KEY_SECRET", "ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    sign = (sign_name or _cfg("ALIYUN_SMS_SIGN_NAME")).strip()
    tpl = (template_code or _cfg("ALIYUN_SMS_TEMPLATE_CODE", "ALIYUN_SMS_TEMPLATE_CODE_RESET")).strip()
    if not (ak and sk and sign and tpl):
        return False, "阿里云短信未配置（需 AccessKey / SignName / TemplateCode）"

    mobile = normalize_cn_mobile(phone)
    import json

    params: Dict[str, str] = {
        "AccessKeyId": ak,
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": mobile,
        "RegionId": _cfg("ALIYUN_SMS_REGION") or "cn-hangzhou",
        "SignName": sign,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(uuid.uuid4()),
        "SignatureVersion": "1.0",
        "TemplateCode": tpl,
        "TemplateParam": json.dumps(template_param, ensure_ascii=False, separators=(",", ":")),
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    sorted_keys = sorted(params.keys())
    canonical = "&".join(f"{_percent_encode(k)}={_percent_encode(params[k])}" for k in sorted_keys)
    string_to_sign = f"GET&{_percent_encode('/')}&{_percent_encode(canonical)}"
    params["Signature"] = _sign(sk, string_to_sign)

    try:
        resp = requests.get(ENDPOINT, params=params, timeout=timeout)
        data = resp.json() if resp.content else {}
    except Exception as exc:
        logger.warning("aliyun sms request error: %s", exc)
        return False, f"请求失败: {exc}"

    code = str(data.get("Code") or "")
    if code == "OK":
        return True, str(data.get("BizId") or "OK")
    msg = str(data.get("Message") or data)[:200]
    logger.warning("aliyun sms fail phone=%s code=%s msg=%s", mobile[:3] + "****" + mobile[-4:], code, msg)
    return False, f"{code}: {msg}" if code else msg


def send_password_reset_code(phone: str, code: str) -> Tuple[bool, str]:
    """模板变量默认 code；可用 ALIYUN_SMS_TEMPLATE_PARAM_KEY 改名。"""
    key = _cfg("ALIYUN_SMS_TEMPLATE_PARAM_KEY") or "code"
    return send_sms(phone, template_param={key: str(code)})
