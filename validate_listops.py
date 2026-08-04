#!/usr/bin/env python3
"""
Local load-time validation for the ListOps plugin — mimics what Claude Code's
plugin loader checks, plus script-reference resolution and Python compile.
Stdlib only. Run from the dra-intelligence repo root.
"""
import ast
import json
import re
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

def frontmatter(p):
    """Minimal --- delimited top-level key:value parser (no pyyaml dep)."""
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip("\n")
    fm = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm

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
    check("evergreen" in servers, ".mcp.json defines evergreen server")
    s = servers.get("evergreen", {})
    check(s.get("type") == "http" and bool(s.get("url")), "evergreen is http with url")

hooks, e = load_json(PLUGIN / "hooks" / "hooks.json")
check(hooks is not None, "hooks/hooks.json is valid JSON", e or "")
if hooks:
    session_start = (hooks.get("hooks") or {}).get("SessionStart")
    check(isinstance(session_start, list) and len(session_start) > 0,
          "hooks.json registers a SessionStart hook")
    commands = [h.get("command", "")
                for group in (session_start or []) for h in (group.get("hooks") or [])]
    # The whole one-step setup rests on this hook firing; a typo here degrades silently
    # into "user must run /listops:connect", which is exactly what it exists to avoid.
    check(any("connect.py bootstrap" in c for c in commands),
          "SessionStart invokes connect.py bootstrap")

src = (PLUGIN / "scripts" / "connect.py").read_text(encoding="utf-8")
check('"bootstrap"' in src, "connect.py registers the bootstrap subcommand")
check("mcpOAuth" in src, "connect.py reads the connector's stored OAuth credential")

print("\n== Frontmatter (commands / agents / skills) ==")
for cmd in sorted((PLUGIN / "commands").glob("*.md")):
    fm = frontmatter(cmd)
    check(fm is not None and bool(fm.get("description")), f"command {cmd.name}: description", "missing/empty frontmatter")
for ag in sorted((PLUGIN / "agents").glob("*.md")):
    fm = frontmatter(ag)
    check(fm is not None and bool(fm.get("name")) and bool(fm.get("description")), f"agent {ag.name}: name+description")
for sk in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
    fm = frontmatter(sk)
    label = sk.parent.name
    check(fm is not None and bool(fm.get("description")), f"skill {label}: description")

print("\n== ${CLAUDE_PLUGIN_ROOT} script references resolve ==")
ref_re = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
missing = 0
for md in [*sorted(PLUGIN.rglob("*.md")), PLUGIN / "hooks" / "hooks.json"]:
    if not md.exists():
        continue
    for rel in ref_re.findall(md.read_text(encoding="utf-8")):
        rel = rel.rstrip(".,);:`'\"")
        if "*" in rel or rel.endswith("/"):
            continue
        target = PLUGIN / rel
        if not target.exists():
            missing += 1
            check(False, f"ref in {md.name} -> {rel}", "target missing")
check(missing == 0, f"all ${{CLAUDE_PLUGIN_ROOT}} file references resolve ({missing} missing)")

print("\n== Python scripts compile ==")
for py in sorted(PLUGIN.rglob("*.py")):
    try:
        ast.parse(py.read_text(encoding="utf-8"))
        check(True, f"compiles: {py.relative_to(PLUGIN)}")
    except SyntaxError as e:
        check(False, f"compiles: {py.relative_to(PLUGIN)}", str(e))

print(f"\n==== {len(ok)} passed, {len(fail)} failed ====")
if fail:
    print("FAILURES:")
    for f in fail:
        print("  - " + f)
sys.exit(1 if fail else 0)
