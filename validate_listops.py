#!/usr/bin/env python3
"""
Local load-time validation for the ListOps plugin: the manifests Claude Code's plugin
loader reads, and the one MCP server it carries. Stdlib only. Run from the repo root.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PLUGIN = ROOT / "plugins" / "listops"
ok, fail = [], []
def check(cond, label, detail=""):
    (ok if cond else fail).append(label)
    print(f"  [{'+' if cond else 'x'}] {label}" + ("" if cond else f"  -- {detail}"))
    return cond

def load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, str(e)

print("== Manifests ==")
mkt, e = load_json(ROOT / ".claude-plugin" / "marketplace.json")
check(mkt is not None, "marketplace.json is valid JSON", e or "")
if mkt:
    check(bool(mkt.get("name")), "marketplace.name present")
    check(isinstance(mkt.get("plugins"), list) and len(mkt["plugins"]) > 0, "marketplace.plugins[] non-empty")
    for pl in mkt.get("plugins", []):
        check(bool(pl.get("name")) and bool(pl.get("source")), f"plugin entry '{pl.get('name')}' has name+source")
        src = ROOT / pl["source"]
        check(src.is_dir(), f"source path resolves: {pl['source']}", "missing dir")

pj, e = load_json(PLUGIN / ".claude-plugin" / "plugin.json")
check(pj is not None, "plugin.json is valid JSON", e or "")
if pj:
    check(bool(pj.get("name")), "plugin.json name present")

mcp, e = load_json(PLUGIN / ".mcp.json")
check(mcp is not None, ".mcp.json is valid JSON", e or "")
if mcp:
    servers = mcp.get("mcpServers", {})
    check("listops" in servers, ".mcp.json defines listops server")
    s = servers.get("listops", {})
    check(s.get("type") == "http" and bool(s.get("url")), "listops is http with url")

check(not (PLUGIN / "hooks").exists(), "plugin ships no hooks — it is the connector config only")
check(not (PLUGIN / "commands").exists(), "plugin ships no slash commands")
check(not (PLUGIN / "scripts").exists(), "plugin ships no scripts")

print(f"\n==== {len(ok)} passed, {len(fail)} failed ====")
if fail:
    print("FAILURES:")
    for f in fail:
        print("  - " + f)
sys.exit(1 if fail else 0)
