---
description: Display LLM token usage summary grouped by date, API endpoint, and model
allowed-tools: ["Bash"]
---

Run the following shell command and output its result as a markdown table:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/token_used.py display
```

Present the table exactly as-is. Do not add explanations unless the output says "No token usage data recorded yet."
