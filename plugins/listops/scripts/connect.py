#!/usr/bin/env python3
"""
connect.py — authorize Claude Code for DRA and install the ListOps skill pack.

The public plugin is a thin bootstrap. The real skills/commands/agent are NOT
shipped in the marketplace — they're downloaded from the DRA API (gated by a
valid, org-validated key) and written under the user's Claude config dir.

Normally nothing here is run by hand: authorizing the `listops` connector is the only
setup step, and the SessionStart hook calls `bootstrap` to finish the job. The OAuth
access token IS the user's dra_ key, so the credential is already on disk by then.

  bootstrap           SessionStart hook: install/refresh the pack using the connector's
                      OAuth token. Silent when there is nothing to do; never fails a session
  set --key dra_xxx   fallback: validate the key, store it in user settings.json, then
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
SERVER_NAME = "listops"
# Names this connector shipped under before. A stale entry points at the same URL as the
# current one, and two entries on one URL means every tool shows up twice.
LEGACY_SERVER_NAMES = ("dra-research", "evergreen")
# Written by Claude Code when a connector completes OAuth. Its format is Claude Code's,
# not ours, so every read is best-effort: unreadable means "not authorized yet".
CREDENTIALS_FILE = ".credentials.json"
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
        url = data["mcpServers"][SERVER_NAME]["url"]
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


def oauth_token():
    """The dra_ key that connector OAuth already persisted, or None.

    This is what makes the second setup step unnecessary: the DRA authorization server
    is bring-your-own-key, so the access token it issues IS the user's dra_ key. Once
    the connector is authorized the credential is already on disk — asking the user to
    paste it a second time is asking for something we can just read.

    Claude Code owns this file's shape, so treat every surprise as "not available"
    rather than an error; the caller falls back to a configured DRA_API_KEY.
    """
    try:
        data = json.loads((config_dir() / CREDENTIALS_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    entries = data.get("mcpOAuth")
    if not isinstance(entries, dict):
        return None
    # Entry keys are scope-namespaced and vary by install method — "listops" when added
    # directly, "plugin:listops:listops" via the marketplace. Match the server name as a
    # path segment instead of pinning one spelling.
    for name, entry in entries.items():
        if not isinstance(entry, dict) or SERVER_NAME not in str(name).split(":"):
            continue
        token = entry.get("accessToken")
        if isinstance(token, str) and token.startswith(KEY_PREFIX):
            return token
    return None


def store_key(key, with_mcp_server):
    """Persist the key in settings.json; optionally add the header-auth server entry.

    with_mcp_server=False is the OAuth path: the connector already exists (from the
    plugin's .mcp.json, authorized via OAuth), so writing a same-named entry here would
    register a SECOND server on the same URL and duplicate all 24 tools.

    Returns True if the key was already present.
    """
    path = settings_path()
    data = load_settings(path)

    env = data.get("env") if isinstance(data.get("env"), dict) else {}
    existing = env.get(ENV_VAR)
    env[ENV_VAR] = key
    data["env"] = env

    mcp_servers = data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else {}
    if with_mcp_server:
        base = mcp_base_url() or "https://api.acqwired.com/v1"
        mcp_servers[SERVER_NAME] = {
            "type": "http",
            "url": f"{base}/mcp",
            "headers": {"Authorization": f"Bearer {key}"},
        }
    for stale in LEGACY_SERVER_NAMES:
        if stale in mcp_servers:
            del mcp_servers[stale]
            print(f"Removed the superseded '{stale}' MCP server (now '{SERVER_NAME}').")
    if mcp_servers:
        data["mcpServers"] = mcp_servers
    else:
        data.pop("mcpServers", None)

    write_json_atomic(path, data)
    return bool(existing)


def install_pack(key, quiet=False):
    """Download the key-gated ListOps pack and write it under the config dir.

    Returns (version, file_count). `quiet` suppresses the progress chatter for the
    SessionStart path, whose stdout lands in Claude's context — one summary line there
    is useful, five are noise.
    """
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
    # Files retired from the pack — remove local copies an older install left
    # behind (the installer overwrites but never prunes).
    LEGACY = {
        "skills/list-operations/assets/pe-platforms.txt": "PE blocklist (now applied server-side at discovery)",
        "commands/listops/conflict-check.md": "conflict-check command (renamed to /listops:signoff)",
    }
    served = {f["path"] for f in files}
    for rel, why in LEGACY.items():
        target = cfg / rel
        if target.exists() and rel not in served:
            try:
                target.unlink()
                if not quiet:
                    print(f"Removed legacy {why}.")
            except OSError:
                pass
    if not quiet:
        print(f"Installed {len(files)} ListOps files (pack {version}) under {cfg}")
    return version, len(files)


def installed_pack_version():
    """Version stamped by the last successful install, or None if never installed."""
    vf = config_dir() / VERSION_FILE
    try:
        return vf.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def cmd_set(args):
    key = validate_key(args.key)
    # Manual path: the user pasted a key rather than authorizing the connector, so also
    # write the header-auth server entry — there may be no OAuth-backed connector at all.
    existing = store_key(key, with_mcp_server=True)
    print(f"{'Updated' if existing else 'Saved'} {ENV_VAR}={mask(key)} in {settings_path()}")
    if os.environ.get(ENV_VAR) and os.environ[ENV_VAR] != key:
        print(f"NOTE: a different {ENV_VAR} is set in your shell and takes precedence -- unset or align it.")

    print("Downloading the ListOps skill pack...")
    install_pack(key)
    print()
    print(f"NEXT: restart Claude Code once -- the keyed {SERVER_NAME} MCP server and the")
    print("downloaded skills/commands/agent all load at startup. Then run /listops:status.")


def cmd_bootstrap(args):
    """SessionStart entry point — finish setup from the token OAuth already stored.

    Runs on every session start, so it stays quiet unless it did something. Its stdout is
    injected into Claude's context, and it must never block a session: every failure path
    returns normally instead of raising, and the worst case is the manual instruction the
    user would have followed anyway.
    """
    installed = installed_pack_version()

    # Prefer the connector's credential — it needs no setup at all. Fall back to a key
    # configured some other way (shell env, settings.json, CI): those users deserve the
    # same automatic refresh, and without this fallback their pack silently rots. A stale
    # pack is not cosmetic — it pins tool names, so a rename leaves the qa-judge agent
    # holding an allowlist of tools that no longer exist.
    token, via_connector = oauth_token(), True
    if not token:
        stored = resolve_key()
        token, via_connector = (stored if stored and stored.startswith(KEY_PREFIX) else None), False

    if not token:
        if not installed:
            print(f"ListOps: the '{SERVER_NAME}' connector is not authorized yet — authorize it "
                  f"(/mcp -> {SERVER_NAME} -> Authenticate) and the pipeline installs itself on "
                  f"the next start. Headless? Set {ENV_VAR}=dra_... in the environment instead.")
        return

    shell_key = os.environ.get(ENV_VAR)
    if via_connector and shell_key and shell_key != token:
        print(f"ListOps: a different {ENV_VAR} is set in your shell and takes precedence "
              "over the connector's credential — unset or align it if the pipeline misbehaves.")

    if installed:
        # A version we can read back means the server accepted this token, so it is safe
        # to refresh the stored copy (tokens can be rotated). None is ambiguous —
        # unreachable or rejected — so leave the working setup alone.
        latest = server_pack_version(token)
        if not latest:
            return
        if via_connector:
            store_key(token, with_mcp_server=False)
        if latest != installed:
            try:
                version, count = install_pack(token, quiet=True)
            except SystemExit:
                return  # keep the pack that works; the next session retries
            print(f"ListOps: pack updated {installed} -> {version} ({count} files). "
                  "Restart Claude Code if commands or the agent changed.")
        return

    # Never installed. Download FIRST: the request is what proves the token is good, and
    # persisting a credential the API rejects would leave the pipeline holding a dead key.
    try:
        version, count = install_pack(token, quiet=True)
    except SystemExit:
        print("ListOps: the credential was rejected by the API, so the pack was not "
              f"installed. Re-authorize the '{SERVER_NAME}' connector, or check the "
              f"{ENV_VAR} you have configured.")
        return
    if via_connector:
        store_key(token, with_mcp_server=False)
    origin = (f"using the '{SERVER_NAME}' connector credential — no separate key needed"
              if via_connector else "using your stored key")
    print(f"ListOps: installed {count} pack files (version {version}) {origin}. "
          "Restart Claude Code once to load the commands and the qa-judge agent.")


def cmd_update(args):
    key = resolve_key()
    if not key:
        print(f"ERROR: no {ENV_VAR} configured — authorize the {SERVER_NAME} connector "
              f"or set {ENV_VAR}.", file=sys.stderr)
        sys.exit(2)
    install_pack(validate_key(key))
    print("Update complete. Restart Claude Code if commands or the agent changed (skills hot-reload).")


def server_pack_version(key):
    """Fetch the current pack version from the API; None if unreachable."""
    base = mcp_base_url()
    if not base or not key:
        return None
    req = urllib.request.Request(f"{base}/listops/version")
    req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode()).get("version")
    except Exception:
        return None


def cmd_check(args):
    path = settings_path()
    env = load_settings(path).get("env")
    in_settings = env.get(ENV_VAR) if isinstance(env, dict) else None
    in_shell = os.environ.get(ENV_VAR)
    print(f"shell env:     {ENV_VAR}={mask(in_shell)}  (takes precedence)" if in_shell else f"shell env:     {ENV_VAR} not set")
    print(f"settings.json: {ENV_VAR}={mask(in_settings)}  ({path})" if in_settings else f"settings.json: {ENV_VAR} not set  ({path})")
    vf = config_dir() / VERSION_FILE
    installed = vf.read_text(encoding="utf-8").strip() if vf.exists() else None
    print(f"skill pack:    {installed} installed" if installed else f"skill pack:    not installed (authorize the {SERVER_NAME} connector, then restart)")
    latest = server_pack_version(in_shell or in_settings)
    if latest and installed and latest != installed:
        print(f"               OUTDATED — server has {latest}; the next session start updates it.")
    elif latest and installed:
        print("               up to date")
    if not in_shell and not in_settings:
        print(f"\nNot connected. Authorize the {SERVER_NAME} connector, or set {ENV_VAR}.")
        sys.exit(2)


def cmd_clear(args):
    path = settings_path()
    data = load_settings(path)
    changed = False

    env = data.get("env")
    if isinstance(env, dict) and ENV_VAR in env:
        del env[ENV_VAR]
        if not env:
            data.pop("env", None)
        changed = True
        print(f"Removed {ENV_VAR} from {path}.")
    else:
        print(f"{ENV_VAR} was not set in {path}; nothing to do.")

    # Also remove the MCP server auth config written by cmd_set, plus anything left by a
    # name this connector shipped under previously.
    mcp = data.get("mcpServers")
    if isinstance(mcp, dict):
        for name in (SERVER_NAME, *LEGACY_SERVER_NAMES):
            if name in mcp:
                del mcp[name]
                changed = True
                print(f"Removed {name} MCP server config from settings.json.")
        if not mcp:
            data.pop("mcpServers", None)

    if changed:
        write_json_atomic(path, data)
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

    b = sub.add_parser("bootstrap", help="SessionStart hook: install/refresh the pack using the connector's OAuth token")
    b.set_defaults(func=cmd_bootstrap)

    args = p.parse_args()
    if args.cmd == "bootstrap":
        # A session must start even if setup cannot. install_pack() and friends exit(3) on
        # network or auth trouble, which would surface as a failing hook; swallow all of it.
        try:
            cmd_bootstrap(args)
        except SystemExit:
            pass
        except Exception:
            pass
        return
    args.func(args)


if __name__ == "__main__":
    main()
