#!/usr/bin/env python3
"""Keep what Kiro loads from this folder in step with the plugins. Standard library only.

    python3 tests/sync_kiro.py           rewrite .kiro/skills/<name>/SKILL.md and .kiro/agents/<name>.md from plugins/
    python3 tests/sync_kiro.py --check   exit 1 and name every file that differs (check_plugins.py runs this)

The real skills stay in plugins/<power>/skills/<name>/SKILL.md and the real agents in plugins/kirocut/agents/<name>.md.
Kiro loads `.kiro/skills/*` and `.kiro/agents/*` when this folder opens, so each skill there is a short stub that sends the agent
to the real file and says what the two path variables mean; each agent is a copy.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POWERS = ("kirocut", "style-match")

STUB = """---
name: {name}
description: {description}
license: {license}
---

# {name}

Kiro loaded this copy so the skill is available in this folder. Read and follow `plugins/{power}/skills/{name}/SKILL.md` in full before doing anything else.

In that file, `${{KIROCUT_SKILL}}` means `plugins/{power}/skills/{name}` and `${{KIROCUT_PLUGIN}}` means `plugins/{power}`. Those paths start at the root of this repo. They are not the folder this file is in.
"""


def head(path):
    t = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    h = t.split("\n---\n", 1)[0].removeprefix("---\n")
    return {k.strip(): v.strip() for k, v in (ln.split(":", 1) for ln in h.splitlines() if re.match(r"^[a-z-]+:", ln))}


def wanted():
    """{path relative to the repo: the text it should have}."""
    out = {}
    for power in POWERS:
        for src in sorted((ROOT / "plugins" / power / "skills").glob("*/SKILL.md")):
            fm = head(src)
            out[f".kiro/skills/{src.parent.name}/SKILL.md"] = STUB.format(
                name=src.parent.name, description=fm["description"].replace('"', "'"), license=fm.get("license", "MIT"), power=power)
    for power in POWERS:
        for src in sorted((ROOT / "plugins" / power / "agents").glob("*.md")):
            out[f".kiro/agents/{src.name}"] = src.read_text(encoding="utf-8").replace("\r\n", "\n")
    return out


def drift():
    """The files under .kiro/ that differ from what the plugins say they should be."""
    out = []
    for rel, text in wanted().items():
        f = ROOT / rel
        if (f.read_text(encoding="utf-8").replace("\r\n", "\n") if f.is_file() else None) != text:
            out.append(rel)
    return out


def main(argv):
    check = "--check" in argv
    bad = drift()
    if not check:
        for rel, text in wanted().items():
            if rel in bad:
                f = ROOT / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(text.encode("utf-8"))
    if check:
        for rel in bad:
            print(f"FAIL {rel}: out of step with plugins/; run python3 tests/sync_kiro.py")
        return 1 if bad else 0
    print(f"{len(bad)} file(s) written" if bad else "already in step")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
