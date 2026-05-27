#!/usr/bin/env python3
"""Configure token-used statusLine in Claude Code settings.json."""
import json
import os
import stat
import sys

CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
SETTINGS_FILE = os.path.join(CLAUDE_DIR, "settings.json")
DATA_DIR = os.path.join(CLAUDE_DIR, "plugins", "data", "token-used-howie-plugins")
WRAPPER_FILE = os.path.join(DATA_DIR, "combined_statusline.sh")


def get_plugin_root():
    root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not root:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return root


def read_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def make_combined_wrapper(existing_cmd, token_cmd):
    """Write a bash wrapper that runs both commands and joins their output with ' | '."""
    os.makedirs(DATA_DIR, exist_ok=True)
    script = (
        "#!/bin/bash\n"
        f"HUD_OUTPUT=$( {existing_cmd} 2>/dev/null )\n"
        f"TOKEN_OUTPUT=$( {token_cmd} 2>/dev/null )\n"
        'if [ -n "$HUD_OUTPUT" ] && [ -n "$TOKEN_OUTPUT" ]; then\n'
        '    printf "%s | %s" "$HUD_OUTPUT" "$TOKEN_OUTPUT"\n'
        'elif [ -n "$HUD_OUTPUT" ]; then\n'
        '    printf "%s" "$HUD_OUTPUT"\n'
        'else\n'
        '    printf "%s" "$TOKEN_OUTPUT"\n'
        'fi\n'
    )
    with open(WRAPPER_FILE, "w", encoding="utf-8") as f:
        f.write(script)
    os.chmod(
        WRAPPER_FILE,
        stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
    )
    return WRAPPER_FILE


def main():
    plugin_root = get_plugin_root()
    token_cmd = f"python3 {plugin_root}/scripts/token_used.py statusline"

    try:
        settings = read_settings()
    except Exception as e:
        print(f"Error reading {SETTINGS_FILE}: {e}", file=sys.stderr)
        sys.exit(1)

    existing = settings.get("statusLine")

    if not existing:
        settings["statusLine"] = {"type": "command", "command": token_cmd}
        write_settings(settings)
        print("✅ token-used statusLine configured.")
        print("Restart Claude Code for the change to take effect.")
        return

    existing_cmd = existing.get("command", "") if isinstance(existing, dict) else str(existing)

    if "token_used.py" in existing_cmd:
        print("token-used statusLine is already configured.")
        return

    # Another statusLine exists — create a combined wrapper that appends token info.
    # Running the existing command inside $( ) captures its stdout even when the
    # command uses `exec` internally (exec only replaces the subshell).
    wrapper_path = make_combined_wrapper(existing_cmd, token_cmd)
    settings["statusLine"] = {"type": "command", "command": f"bash {wrapper_path}"}
    write_settings(settings)
    print(f"✅ Combined statusLine configured.")
    print(f"   Wrapper: {wrapper_path}")
    print("Restart Claude Code for the change to take effect.")


if __name__ == "__main__":
    main()
