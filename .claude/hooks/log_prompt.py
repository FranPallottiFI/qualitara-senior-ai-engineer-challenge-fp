#!/usr/bin/env python3
"""UserPromptSubmit hook: append every prompt I type, verbatim, to ai-log/raw-prompts.md.

Why a hook: the AI log must be raw. A hook records prompts as they happen, outside the agent's
control (agents are denied Edit/Write on this file), so the log can't be tidied afterwards.
Stdlib only. Never blocks the prompt: any failure exits 0 silently.
"""

import json
import os
import sys
from datetime import datetime


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    prompt = data.get("prompt", "")
    if not prompt.strip():
        return
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."
    path = os.path.join(root, "ai-log", "raw-prompts.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    new_file = not os.path.exists(path)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    session = str(data.get("session_id", ""))[:8]
    fence = "````" if "```" in prompt else "```"

    with open(path, "a", encoding="utf-8") as f:
        if new_file:
            f.write(
                "# Raw prompts\n\nAppended automatically by `.claude/hooks/log_prompt.py` "
                "on every prompt I submit. Not edited by hand or by agents.\n"
            )
        f.write(f"\n### {ts} · session `{session}`\n\n{fence}text\n{prompt}\n{fence}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
