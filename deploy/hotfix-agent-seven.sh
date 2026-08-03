#!/bin/bash
# 七项 Agent 后台增强热更：api + dingtalk-agent + 前端 dist
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"
cd /opt/backpack-quant

append_env() {
  local key="$1" val="$2"
  if ! grep -q "^${key}=" .env 2>/dev/null; then
    echo "${key}=${val}" >> .env
    echo "appended ${key}=${val}"
  fi
}

append_env AGENT_PATROL_ENABLED 1
append_env AGENT_PATROL_HOUR 9
append_env AGENT_AUTO_REVIEW_ENABLED 1
append_env AGENT_AUTO_REVIEW_DAYS 3
append_env AGENT_WEEKLY_DINGTALK 1
append_env AGENT_API_BASE http://api:8100

inject() {
  local c="$1"
  docker exec "$c" mkdir -p \
    /app/backpack_quant_trading/agents \
    /app/backpack_quant_trading/api/routers \
    /app/backpack_quant_trading/frontend/src/views \
    /app/backpack_quant_trading/frontend/src/api \
    /app/backpack_quant_trading/frontend/src/layouts \
    /app/backpack_quant_trading/frontend/dist || true

  docker cp backpack_quant_trading/agents/steward_agent.py "$c:/app/backpack_quant_trading/agents/steward_agent.py"
  docker cp backpack_quant_trading/agents/steward_trading.py "$c:/app/backpack_quant_trading/agents/steward_trading.py"
  docker cp backpack_quant_trading/agents/dingtalk_bridge.py "$c:/app/backpack_quant_trading/agents/dingtalk_bridge.py"
  docker cp backpack_quant_trading/agents/dingtalk_push.py "$c:/app/backpack_quant_trading/agents/dingtalk_push.py"
  docker cp backpack_quant_trading/agents/patrol_agent.py "$c:/app/backpack_quant_trading/agents/patrol_agent.py"
  docker cp backpack_quant_trading/agents/self_heal.py "$c:/app/backpack_quant_trading/agents/self_heal.py"
  docker cp backpack_quant_trading/agents/execution_agent.py "$c:/app/backpack_quant_trading/agents/execution_agent.py"
  docker cp backpack_quant_trading/agents/review_agent.py "$c:/app/backpack_quant_trading/agents/review_agent.py"
  docker cp backpack_quant_trading/agents/coordinator.py "$c:/app/backpack_quant_trading/agents/coordinator.py"
  docker cp backpack_quant_trading/agents/formatters.py "$c:/app/backpack_quant_trading/agents/formatters.py"
  docker cp backpack_quant_trading/agents/scheduler_hooks.py "$c:/app/backpack_quant_trading/agents/scheduler_hooks.py"
  docker cp backpack_quant_trading/core/binance_monitor.py "$c:/app/backpack_quant_trading/core/binance_monitor.py"
  docker cp backpack_quant_trading/core/binance_client.py "$c:/app/backpack_quant_trading/core/binance_client.py"
  docker cp backpack_quant_trading/strategy/adaptive_long_strategy.py "$c:/app/backpack_quant_trading/strategy/adaptive_long_strategy.py"
  docker cp backpack_quant_trading/strategy/adaptive_short_strategy.py "$c:/app/backpack_quant_trading/strategy/adaptive_short_strategy.py"
  docker cp backpack_quant_trading/api/main.py "$c:/app/backpack_quant_trading/api/main.py"
  docker cp backpack_quant_trading/api/routers/trading.py "$c:/app/backpack_quant_trading/api/routers/trading.py"
  docker cp backpack_quant_trading/api/routers/agent_memory.py "$c:/app/backpack_quant_trading/api/routers/agent_memory.py"
  docker cp backpack_quant_trading/api/routers/steward.py "$c:/app/backpack_quant_trading/api/routers/steward.py"
}

inject backpack-api
inject backpack-dingtalk-agent

# 前端静态资源（记忆面板）
if [ -d backpack_quant_trading/frontend/dist ]; then
  docker cp backpack_quant_trading/frontend/dist/. backpack-api:/app/backpack_quant_trading/frontend/dist/
fi

# 同步 .env 进容器（compose 常挂载；无挂载时复制）
docker cp .env backpack-api:/app/.env 2>/dev/null || true
docker cp .env backpack-dingtalk-agent:/app/.env 2>/dev/null || true

docker restart backpack-api backpack-dingtalk-agent
sleep 25
curl -sf http://127.0.0.1:8100/api/health
echo

docker exec backpack-api python - <<'PY'
from backpack_quant_trading.agents.steward_agent import parse_steward_intent
from backpack_quant_trading.agents.execution_agent import parse_exec_command
from backpack_quant_trading.api.routers import agent_memory, steward
from backpack_quant_trading.agents.patrol_agent import format_patrol_markdown
from backpack_quant_trading.agents.review_agent import auto_review_due_reports
print('parse', parse_steward_intent('查看策略实例').action, parse_exec_command('待确认列表'))
print('routes steward', len(steward.router.routes), 'memory', len(agent_memory.router.routes))
print('import_ok')
PY

TOK=$(grep -E '^(AGENT_STEWARD_TOKEN|WEBHOOK_SECRET)=' .env | head -1 | cut -d= -f2-)
export STEWARD_TOK="$TOK"

python3 - <<'PY'
import json, os, urllib.request

tok = os.environ.get("STEWARD_TOK") or ""
url = "http://127.0.0.1:8100/api/steward/command"

def call(text):
    body = json.dumps({"text": text, "staff_id": "deploy"}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            md = (data.get("markdown") or "")[:320]
            print("OK", data.get("ok"), md.replace("\n", " | "))
    except Exception as e:
        print("ERR", e)

print("CASE: 查看策略实例")
call("查看策略实例")
print("CASE: 实例日志")
call("实例日志")

# 记忆 API 需 JWT；仅检查 openapi / 路由存在
req = urllib.request.Request("http://127.0.0.1:8100/openapi.json")
with urllib.request.urlopen(req, timeout=30) as resp:
    spec = json.loads(resp.read().decode())
paths = spec.get("paths") or {}
print("has /api/agent-memory/stats", "/api/agent-memory/stats" in paths)
print("has brief", any("/brief" in p for p in paths))

# 巡检函数（不推钉钉）
import subprocess, textwrap
subprocess.check_call([
    "docker", "exec", "backpack-api", "python", "-c",
    "from backpack_quant_trading.agents.patrol_agent import run_daily_patrol; "
    "r=run_daily_patrol(push=False); print('patrol', r.get('ok'), 'pending', (r.get('snapshot') or {}).get('pending_total'))"
])
PY

docker ps --format '{{.Names}} {{.Status}}' | grep -E 'api|dingtalk' || true
echo DONE
