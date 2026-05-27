#!/usr/bin/env python3
"""
token-used: Claude Code plugin to track LLM token usage.
Modes: record | statusline | display
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict

DATA_DIR = os.path.expanduser("~/.claude/token-used")
USAGE_FILE = os.path.join(DATA_DIR, "usage.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")


def ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def format_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def prune_old_records(records):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    return [r for r in records if r.get("timestamp", "") >= cutoff]


# ── record mode ──────────────────────────────────────────────────────────────

def cmd_record():
    """
    Reads session_id and transcript_path from the hook JSON on stdin.
    Falls back to environment variables for manual invocation.
    """
    ensure_dir()

    session_id = ""
    transcript_path = ""

    # Try stdin first (hook system passes JSON with session_id + transcript_path)
    try:
        hook_data = json.load(sys.stdin)
        session_id = hook_data.get("session_id", "")
        transcript_path = hook_data.get("transcript_path", "")
    except Exception:
        pass

    # Fallback to environment variables
    if not session_id:
        session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if not transcript_path:
        transcript_path = os.environ.get("CLAUDE_TRANSCRIPT_PATH", "")

    if not transcript_path or not os.path.exists(transcript_path):
        return

    # Read transcript entries
    entries = []
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        return

    # Collect assistant messages that have usage data, in order
    assistant_msgs = [
        e for e in entries
        if e.get("type") == "assistant"
        and isinstance(e.get("message"), dict)
        and e["message"].get("usage")
    ]

    if not assistant_msgs:
        return

    # State tracks how many messages per session have been recorded
    state = load_json(STATE_FILE, {})
    already_processed = state.get(session_id, 0)
    new_msgs = assistant_msgs[already_processed:]

    if not new_msgs:
        return

    # API base URL from env (set in Claude Code settings)
    api_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    api_url = api_url.rstrip("/")

    records = load_json(USAGE_FILE, [])
    records = prune_old_records(records)

    for entry in new_msgs:
        msg = entry["message"]
        usage = msg.get("usage", {})
        model = msg.get("model", "unknown")
        ts = entry.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Normalise timestamp to UTC ISO string
        try:
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts)
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")
            ts = datetime.now(timezone.utc).isoformat()

        records.append({
            "timestamp": ts,
            "date": date_str,
            "session_id": session_id,
            "uuid": entry.get("uuid", ""),
            "api": api_url,
            "model": model,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
            "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
        })

    save_json(USAGE_FILE, records)

    # Update state — keep only the 500 most-recently-seen session ids
    state[session_id] = len(assistant_msgs)
    if len(state) > 500:
        state = dict(list(state.items())[-500:])
    save_json(STATE_FILE, state)


# ── statusline mode ───────────────────────────────────────────────────────────

def cmd_statusline():
    records = load_json(USAGE_FILE, [])
    today = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")

    today_in = today_out = month_total = 0
    for r in records:
        date = r.get("date", "")
        inp = (
            r.get("input_tokens", 0)
            + r.get("cache_read_tokens", 0)
            + r.get("cache_creation_tokens", 0)
        )
        out = r.get("output_tokens", 0)
        if date.startswith(current_month):
            month_total += inp + out
        if date == today:
            today_in += inp
            today_out += out

    print(
        f"In: {format_tokens(today_in)} "
        f"Out: {format_tokens(today_out)} "
        f"Month: {format_tokens(month_total)}",
        end="",
    )


# ── display mode ──────────────────────────────────────────────────────────────

def cmd_display():
    records = load_json(USAGE_FILE, [])
    if not records:
        print("No token usage data recorded yet.")
        return

    # Aggregate by (date, api, model)
    groups = defaultdict(lambda: {"input": 0, "output": 0})
    for r in sorted(records, key=lambda x: x.get("date", ""), reverse=True):
        key = (r.get("date", ""), r.get("api", ""), r.get("model", ""))
        groups[key]["input"] += (
            r.get("input_tokens", 0)
            + r.get("cache_read_tokens", 0)
            + r.get("cache_creation_tokens", 0)
        )
        groups[key]["output"] += r.get("output_tokens", 0)

    col_widths = [10, 30, 20, 10, 10]
    header = ["Date", "API", "Model", "In", "Out"]

    def row_str(cells):
        return "| " + " | ".join(
            str(c).ljust(w) for c, w in zip(cells, col_widths)
        ) + " |"

    separator = "|-" + "-|-".join("-" * w for w in col_widths) + "-|"

    print(row_str(header))
    print(separator)
    for (date, api, model), totals in sorted(groups.items(), reverse=True):
        print(row_str([
            date,
            api,
            model,
            format_tokens(totals["input"]),
            format_tokens(totals["output"]),
        ]))


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "display"
    if mode == "record":
        cmd_record()
    elif mode == "statusline":
        cmd_statusline()
    elif mode == "display":
        cmd_display()
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
