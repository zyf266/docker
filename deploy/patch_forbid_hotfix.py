#!/usr/bin/env python3
"""给 deploy/hotfix*.sh 与 restore-prod-hotfixes.sh 注入禁止热更守卫。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"
GUARD = 'source "$(cd "$(dirname "$0")" && pwd)/_forbid_hotfix.sh"\n'
MARKER = "_forbid_hotfix.sh"

def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    if text.startswith("#!"):
        lines = text.splitlines(keepends=True)
        # after shebang + optional set -e
        i = 1
        while i < len(lines) and (
            lines[i].startswith("#") or lines[i].strip().startswith("set ")
        ):
            i += 1
        new = "".join(lines[:i]) + "\n" + GUARD + "".join(lines[i:])
    else:
        new = "#!/bin/bash\n" + GUARD + text
    path.write_text(new, encoding="utf-8")
    return True

def main() -> None:
    files = sorted(DEPLOY.glob("hotfix*.sh"))
    files.append(DEPLOY / "restore-prod-hotfixes.sh")
    n = 0
    for f in files:
        if not f.is_file():
            continue
        if f.name.startswith("_"):
            continue
        if patch(f):
            print("patched", f.name)
            n += 1
        else:
            print("skip", f.name)
    print("done", n)

if __name__ == "__main__":
    main()
