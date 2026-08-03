# -*- coding: utf-8 -*-
from backpack_quant_trading.agents.dingtalk_bridge import is_steward_command, should_route_to_agent
from backpack_quant_trading.agents.steward_agent import parse_steward_intent

cases = [
    "\u589e\u52a0\u4e00\u4e2aSOL 2h\u7684\u5e01\u79cd\u76d1\u89c6",
    "\u7ed9\u6211\u76d1\u63a7\u4e00\u4e2aNVDA\u5173\u4e8e\u8d22\u62a5\u7684\u65b0\u95fb",
]
for s in cases:
    i = parse_steward_intent(s)
    print("TEXT", s)
    print(" route", should_route_to_agent(s), "steward", is_steward_command(s))
    print(" intent", i.action, i.params, i.note)
    assert should_route_to_agent(s), s
print("OK")
