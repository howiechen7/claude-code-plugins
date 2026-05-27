---
description: Set up token-used statusLine in Claude Code
allowed-tools: ["Bash"]
---

Run the following command to configure the token-used statusLine:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/setup.py
```

This will:
- Write token usage info into Claude Code's statusLine
- If another statusLine (e.g. claude-hud) is already configured, automatically create a combined wrapper that shows both side by side

After the command completes, **restart Claude Code** for the change to take effect.
