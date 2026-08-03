#!/usr/bin/env python3
"""查看评分反馈 / Agent 记忆向量库，便于验证「有没有学到」。

用法（项目根或容器内）:
  python -m backpack_quant_trading.tools.inspect_chroma_memory
  python -m backpack_quant_trading.tools.inspect_chroma_memory --query "偏保守 TSM 轻仓试错" --symbol TSM
  python -m backpack_quant_trading.tools.inspect_chroma_memory --kind agent_prefs --query "更严止损"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from backpack_quant_trading.core.env_loader import load_project_env

    load_project_env()
except Exception:
    pass


def _print_hits(title: str, hits: list) -> None:
    print(f"\n=== {title} ({len(hits)}) ===")
    if not hits:
        print("(空)")
        return
    for i, h in enumerate(hits, 1):
        meta = h.get("metadata") or {}
        dist = h.get("distance")
        dist_s = f"{dist:.4f}" if isinstance(dist, (int, float)) else str(dist)
        doc = (h.get("document") or "")[:220].replace("\n", " ")
        print(f"\n#{i} id={h.get('id')} distance={dist_s}")
        print(f"  meta: {json.dumps(meta, ensure_ascii=False)[:400]}")
        print(f"  doc:  {doc}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect Chroma score_feedback / agent memory")
    ap.add_argument("--query", default="", help="语义检索文本；空则只统计数量并抽样 peek")
    ap.add_argument("--symbol", default="", help="评分反馈按 symbol 过滤（可选）")
    ap.add_argument(
        "--kind",
        default="all",
        choices=["all", "score_feedback", "agent_prefs", "agent_reports", "agent_research", "agent_reviews"],
    )
    ap.add_argument("-n", type=int, default=5, help="检索条数")
    args = ap.parse_args()

    from backpack_quant_trading.core import score_feedback_store as sfs
    from backpack_quant_trading.core import agent_memory_store as ams

    print("SCORE_FEEDBACK_CHROMA_ENABLED =", os.getenv("SCORE_FEEDBACK_CHROMA_ENABLED", "1"))
    print("AGENT_MEMORY_CHROMA_ENABLED   =", os.getenv("AGENT_MEMORY_CHROMA_ENABLED", "1"))
    print("chroma path                  =", sfs._chroma_path())  # noqa: SLF001

    # 评分反馈 collection
    if args.kind in ("all", "score_feedback"):
        col = sfs._get_collection()  # noqa: SLF001
        if col is None:
            print("\n[score_feedback] 不可用（未启用或未装 chromadb）")
        else:
            n = int(col.count())
            print(f"\n[score_feedback] count={n}")
            if args.query.strip():
                hits = sfs.query_similar(args.query, n_results=args.n, symbol=args.symbol)
                _print_hits("score_feedback 检索", hits)
            elif n:
                peek = col.peek(min(args.n, n))
                rows = []
                ids = peek.get("ids") or []
                docs = peek.get("documents") or []
                metas = peek.get("metadatas") or []
                for i, mid in enumerate(ids):
                    rows.append({
                        "id": mid,
                        "document": docs[i] if i < len(docs) else "",
                        "metadata": metas[i] if i < len(metas) else {},
                        "distance": None,
                    })
                _print_hits("score_feedback 抽样 peek", rows)

    # Agent 记忆 collections
    kinds = (
        ["agent_prefs", "agent_reports", "agent_research", "agent_reviews"]
        if args.kind == "all"
        else [args.kind] if args.kind.startswith("agent_") else []
    )
    for kind in kinds:
        if not ams.agent_memory_enabled():
            print(f"\n[{kind}] Agent 记忆已关闭 (AGENT_MEMORY_CHROMA_ENABLED=0)")
            break
        try:
            cnt = ams.count_memory(kind)
        except Exception as exc:
            print(f"\n[{kind}] count 失败: {exc}")
            continue
        print(f"\n[{kind}] count={cnt}")
        if args.query.strip():
            hits = ams.query_memory(kind, args.query, n_results=args.n)
            _print_hits(f"{kind} 检索", hits)
        elif cnt:
            # peek via raw collection
            try:
                c = ams._get_collection(kind)  # noqa: SLF001
                if c is not None:
                    peek = c.peek(min(args.n, cnt))
                    rows = []
                    ids = peek.get("ids") or []
                    docs = peek.get("documents") or []
                    metas = peek.get("metadatas") or []
                    for i, mid in enumerate(ids):
                        rows.append({
                            "id": mid,
                            "document": docs[i] if i < len(docs) else "",
                            "metadata": metas[i] if i < len(metas) else {},
                            "distance": None,
                        })
                    _print_hits(f"{kind} 抽样 peek", rows)
            except Exception as exc:
                print(f"  peek 失败: {exc}")

    print(
        "\n验证学习建议:\n"
        "1) 钉钉回复评分卡纠正 → 本脚本 score_feedback count 应 +1\n"
        "2) 再用同品种评分 → 日志应出现「评分反馈」/ feedback_applied；卡片理由更贴你的纠正\n"
        "3) Agent 偏好：发「纠正偏好：更严止损」→ agent_prefs count +1，下次分析 prompt 会注入\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
