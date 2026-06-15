#!/usr/bin/env python3
"""
connect.py — authorize Claude Code for DRA and install the ListOps skill pack.

The public plugin is a thin bootstrap. The real skills/commands/agent are NOT
shipped in the marketplace — they're downloaded from the DRA API (gated by a
valid, org-validated key) and written under the user's Claude config dir.

  set --key dra_xxx   validate the key, store it in user settings.json, then
                      download + install the ListOps skill pack
  update              re-download + reinstall the pack (uses the stored/env key)
  check               report the configured key + installed pack version (masked)
  clear               remove the key from settings.json (optionally --purge files)

Stdlib only. Files load at Claude Code startup, so a restart is needed after
`set`/`update`.
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ENV_VAR = "DRA_API_KEY"
KEY_PREFIX = "dra_"
MIN_KEY_LEN = 12
PLACEHOLDER = "__LISTOPS_SKILLS__"
VERSION_FILE = ".listops-pack-version"


def config_dir():
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(base) if base else Path.home() / ".claude"


def settings_path():
    return config_dir() / "settings.json"


def mcp_base_url():
    """Derive the API base from the bundled .mcp.json (strip a trailing /mcp)."""
    mcp = Path(__file__).resolve().parent.parent / ".mcp.json"
    try:
        data = json.loads(mcp.read_text(encoding="utf-8"))
        url = data["mcpServers"]["dra-research"]["url"]
    except Exception:
        return None
    return url[:-4] if url.endswith("/mcp") else url.rstrip("/")


def mask(key):
    return KEY_PREFIX + "..." if len(key) <= 8 else f"{key[:7]}...{key[-4:]}"


def load_settings(path):
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        print(f"ERROR: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(3)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ERROR: {path} is not valid JSON ({e}). Fix it and re-run.", file=sys.stderr)
        sys.exit(3)
    if not isinstance(data, dict):
        print(f"ERROR: {path} does not contain a JSON object.", file=sys.stderr)
        sys.exit(3)
    return data


def write_json_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_text_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".dl-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def validate_key(key):
    key = (key or "").strip().strip('"').strip("'")
    if not key:
        print("ERROR: no key provided.", file=sys.stderr)
        sys.exit(2)
    if not key.startswith(KEY_PREFIX):
        print(f"ERROR: DRA keys start with '{KEY_PREFIX}'. Got '{mask(key)}'.", file=sys.stderr)
        sys.exit(2)
    if len(key) < MIN_KEY_LEN:
        print(f"ERROR: key looks too short ({len(key)} chars).", file=sys.stderr)
        sys.exit(2)
    if any(c.isspace() for c in key):
        print("ERROR: key contains whitespace — copy it as a single token.", file=sys.stderr)
        sys.exit(2)
    return key


def resolve_key():
    """For update: prefer the shell env var, else the key stored in settings.json."""
    k = os.environ.get(ENV_VAR)
    if k:
        return k
    env = load_settings(settings_path()).get("env")
    return env.get(ENV_VAR) if isinstance(env, dict) else None


def install_pack(key):
    """Download the key-gated ListOps pack and write it under the config dir."""
    base = mcp_base_url()
    if not base:
        print("ERROR: could not read the MCP url from .mcp.json — cannot locate the skill endpoint.", file=sys.stderr)
        sys.exit(3)
    url = f"{base}/listops/skills"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"ERROR: key rejected ({e.code}) — the ListOps skills were NOT installed. Check the key is valid.", file=sys.stderr)
        else:
            print(f"ERROR: skill download failed ({e.code}) from {url}.", file=sys.stderr)
        sys.exit(3)
    except urllib.error.URLError as e:
        print(f"ERROR: cannot reach {url}: {e.reason}", file=sys.stderr)
        sys.exit(3)

    version = data.get("version", "?")
    files = data.get("files", [])
    if not files:
        print("ERROR: server returned no skill files.", file=sys.stderr)
        sys.exit(3)

    cfg = config_dir()
    skills_base = str(cfg / "skills")
    for f in files:
        # __LISTOPS_SKILLS__ -> the real <configdir>/skills path (handles custom CLAUDE_CONFIG_DIR)
        content = f["content"].replace(PLACEHOLDER, skills_base)
        write_text_atomic(cfg / f["path"], content)
    write_text_atomic(cfg / VERSION_FILE, version)
    print(f"Installed {len(files)} ListOps files (pack {version}) under {cfg}")


def cmd_set(args):
    key = validate_key(args.key)
    path = settings_path()
    data = load_settings(path)
    env = data.get("env") if isinstance(data.get("env"), dict) else {}
    existing = env.get(ENV_VAR)
    env[ENV_VAR] = key
    data["env"] = env
    write_json_atomic(path, data)
    print(f"{'Updated' if existing else 'Saved'} {ENV_VAR}={mask(key)} in {path}")
    if os.environ.get(ENV_VAR) and os.environ[ENV_VAR] != key:
        print(f"NOTE: a different {ENV_VAR} is set in your shell and takes precedence -- unset or align it.")

    print("Downloading the ListOps skill pack...")
    install_pack(key)
    print()
    print("NEXT: restart Claude Code once -- the keyed dra-research MCP server and the")
    print("downloaded skills/commands/agent all load at startup. Then run /listops:status.")


def cmd_update(args):
    key = resolve_key()
    if not key:
        print(f"ERROR: no {ENV_VAR} configured — run /listops:connect <dra_ key> first.", file=sys.stderr)
        sys.exit(2)
    install_pack(validate_key(key))
    print("Update complete. Restart Claude Code if commands or the agent changed (skills hot-reload).")


def cmd_check(args):
    path = settings_path()
    env = load_settings(path).get("env")
    in_settings = env.get(ENV_VAR) if isinstance(env, dict) else None
    in_shell = os.environ.get(ENV_VAR)
    print(f"shell env:     {ENV_VAR}={mask(in_shell)}  (takes precedence)" if in_shell else f"shell env:     {ENV_VAR} not set")
    print(f"settings.json: {ENV_VAR}={mask(in_settings)}  ({path})" if in_settings else f"settings.json: {ENV_VAR} not set  ({path})")
    vf = config_dir() / VERSION_FILE
    print(f"skill pack:    {vf.read_text(encoding='utf-8').strip()} installed" if vf.exists() else "skill pack:    not installed (run /listops:connect)")
    if not in_shell and not in_settings:
        print("\nNot connected. Run: /listops:connect <your dra_ key>")
        sys.exit(2)


def cmd_clear(args):
    path = settings_path()
    data = load_settings(path)
    env = data.get("env")
    if isinstance(env, dict) and ENV_VAR in env:
        del env[ENV_VAR]
        if not env:
            data.pop("env", None)
        write_json_atomic(path, data)
        print(f"Removed {ENV_VAR} from {path}.")
    else:
        print(f"{ENV_VAR} was not set in {path}; nothing to do.")
    if args.purge:
        cfg = config_dir()
        removed = 0
        for rel in ("commands/listops", "skills/list-building", "skills/list-operations",
                    "agents/qa-judge.md", VERSION_FILE):
            target = cfg / rel
            try:
                if target.is_dir():
                    import shutil
                    shutil.rmtree(target); removed += 1
                elif target.exists():
                    target.unlink(); removed += 1
            except OSError:
                pass
        print(f"Purged {removed} installed ListOps path(s) under {cfg}.")
    print("Restart Claude Code to apply.")


def main():
    p = argparse.ArgumentParser(description="Connect Claude Code to DRA and install the ListOps skill pack.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("set", help="store the key + download/install the skill pack")
    s.add_argument("--key", required=True, help="your dra_ API key from the Acqwired dashboard")
    s.set_defaults(func=cmd_set)

    u = sub.add_parser("update", help="re-download + reinstall the skill pack")
    u.set_defaults(func=cmd_update)

    c = sub.add_parser("check", help="report the configured key + installed pack version")
    c.set_defaults(func=cmd_check)

    cl = sub.add_parser("clear", help="remove the key (and --purge installed files)")
    cl.add_argument("--purge", action="store_true", help="also delete the installed ListOps files")
    cl.set_defaults(func=cmd_clear)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
