"""代码/名称互查。"""
from __future__ import annotations

import time

from backpack_quant_trading.agents import a_share_resolve as m
from backpack_quant_trading.api.routers.a_share_ai_agent import _normalize_code_name


def test_resolve_code_and_name_from_maps(monkeypatch=None):
    m._CODE_TO_NAME = {"600519": "贵州茅台", "603629": "利通电子"}
    m._NAME_TO_CODE = {"贵州茅台": "600519", "利通电子": "603629", "茅台": "600519"}
    m._LOADED_AT = time.time()

    def no_em(_q):
        return None

    m._resolve_via_eastmoney_suggest = no_em
    assert m.resolve_a_share_token("600519") == ("600519", "贵州茅台")
    assert m.resolve_a_share_token("贵州茅台") == ("600519", "贵州茅台")
    assert m.resolve_a_share_token("茅台") == ("600519", "茅台")


def test_normalize_fills_name_from_code():
    m._CODE_TO_NAME = {"600519": "贵州茅台"}
    m._NAME_TO_CODE = {"贵州茅台": "600519"}
    m._LOADED_AT = time.time()
    m._resolve_via_eastmoney_suggest = lambda _q: None
    code, name = _normalize_code_name("600519", "")
    assert code == "600519"
    assert name == "贵州茅台"


def test_normalize_fills_code_from_name():
    m._CODE_TO_NAME = {"600519": "贵州茅台"}
    m._NAME_TO_CODE = {"贵州茅台": "600519"}
    m._LOADED_AT = time.time()
    m._resolve_via_eastmoney_suggest = lambda _q: None
    code, name = _normalize_code_name("", "贵州茅台")
    assert code == "600519"
    assert name == "贵州茅台"


if __name__ == "__main__":
    test_resolve_code_and_name_from_maps()
    test_normalize_fills_name_from_code()
    test_normalize_fills_code_from_name()
    print("ok")
