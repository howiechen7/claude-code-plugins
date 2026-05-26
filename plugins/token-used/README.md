# token-used

Track and display Claude Code LLM token usage. Records usage automatically at the end of each session, and provides a `/token-used` slash command to view aggregated stats.

## Features

- **Automatic recording** — hooks into `SessionEnd` to log token usage from every session
- **Status line integration** — shows today's and this month's token counts in the terminal status bar
- **Usage display** — `/token-used` command shows a table grouped by date, API endpoint, and model
- **31-day retention** — automatically prunes records older than 31 days

## Modes

| Mode | Description |
|------|-------------|
| `record` | Reads the transcript and saves token usage to `~/.claude/token-used/usage.json` |
| `statusline` | Outputs today's input/output tokens and monthly total |
| `display` | Prints a markdown table of aggregated usage |

## Data Storage

All data is stored in `~/.claude/token-used/`:
- `usage.json` — token usage records (31-day rolling window)
- `state.json` — tracks which session messages have been processed

## Installation

```bash
/plugin marketplace add howiechen7/claude-code-plugins
/plugin install token-used@howiechen7/claude-code-plugins
```
