"""实例敏感字段 RSA-OAEP 加解密（私钥落盘 data/instance_rsa/）。"""
from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

logger = logging.getLogger(__name__)

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_KEY_DIR = _PACKAGE_ROOT / "data" / "instance_rsa"
_PRIVATE_PATH = _KEY_DIR / "private.pem"
_PUBLIC_PATH = _KEY_DIR / "public.pem"

_private_key = None
_public_key = None


def _ensure_key_dir() -> None:
    _KEY_DIR.mkdir(parents=True, exist_ok=True)


def _generate_keypair() -> None:
    _ensure_key_dir()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _PRIVATE_PATH.write_bytes(private_pem)
    _PUBLIC_PATH.write_bytes(public_pem)
    try:
        os.chmod(_PRIVATE_PATH, 0o600)
    except OSError:
        pass
    logger.info("已生成实例 RSA 密钥对: %s", _KEY_DIR)


def _load_keys():
    global _private_key, _public_key
    if _private_key is not None and _public_key is not None:
        return
    _ensure_key_dir()
    if not _PRIVATE_PATH.is_file() or not _PUBLIC_PATH.is_file():
        _generate_keypair()
    private_pem = _PRIVATE_PATH.read_bytes()
    public_pem = _PUBLIC_PATH.read_bytes()
    _private_key = serialization.load_pem_private_key(private_pem, password=None)
    _public_key = serialization.load_pem_public_key(public_pem)


def encrypt_field(plaintext: str) -> str:
    """RSA-OAEP(SHA-256) 加密，返回 base64 密文。"""
    if plaintext is None or plaintext == "":
        raise ValueError("plaintext 不能为空")
    _load_keys()
    assert _public_key is not None
    data = plaintext.encode("utf-8")
    # RSA-2048 OAEP-SHA256 约可加密 ~190 字节；密钥类字段足够
    ciphertext = _public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(ciphertext).decode("ascii")


def decrypt_field(ciphertext: str) -> str:
    """解密 base64 密文。"""
    if not ciphertext:
        raise ValueError("ciphertext 不能为空")
    _load_keys()
    assert _private_key is not None
    raw = base64.b64decode(ciphertext.encode("ascii"))
    plain = _private_key.decrypt(
        raw,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return plain.decode("utf-8")


def key_paths() -> tuple[Path, Path]:
    return _PRIVATE_PATH, _PUBLIC_PATH
