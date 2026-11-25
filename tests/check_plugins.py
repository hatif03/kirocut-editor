#!/usr/bin/env python3
"""Static checks on the plugin files: manifests, skill and agent frontmatter, shared docs. Stdlib only.

    python3 tests/check_plugins.py

Skill frontmatter follows https://agentskills.io/specification. Each plugin's plugin.json is an
Agent Plugins manifest, which is what Kiro installs as a power.
Exit 1 with one line per problem.
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PATHS_LINE = "Paths: `${KIROCUT_SKILL}` means the folder containing this SKILL.md"
errors = []
KEY_URLS = ("https://aistudio.google.com/apikey",
            "https://elevenlabs.io/app/settings/api-keys", "https://modal.com/signup")
EVALS = [("plugins/kirocut/evals/setup-window-first", "home.py serve"),
         ("plugins/kirocut/evals/setup-window-first", "install-all --report"),
         ("plugins/kirocut/evals/start-asks", "kirocut_ask"),
         ("plugins/kirocut/evals/launch-video-url", "kirocut_ask"),
         ("plugins/kirocut/evals/launch-video-url", "what the video must show"),
         ("plugins/kirocut/evals/render-unapproved", "Approve"),
         ("plugins/kirocut/evals/captions-too-small", "help everyone"),
         ("plugins/kirocut/evals/improve-from-feedback", "improve"),
         ("plugins/kirocut/evals/clips-fan-out", "clip-editor"),
         ("plugins/kirocut/evals/move-card-off-caption", "edit.py patch"),
         ("plugins/kirocut/evals/paste-website-link", "product-video"),
         ("plugins/kirocut/evals/paste-tiktok-profile", "style-match"),
         ("plugins/kirocut/evals/repo-no-plugin", "kiro-cli powers install"),
         ("plugins/kirocut/evals/logo-pack-named-tools", "logo-pack"),
         ("plugins/kirocut/evals/skill-improver-teach", "skill-improver"),
         ("plugins/kirocut/evals/skill-maker-new", "skill-maker"),
         ("plugins/style-match/evals/tear-down-handle", "kirocut_ask")]


# What Kiro must read before a skill's first step: SKILL.md plus every file it says to "Read `X` first".
# Each byte is a token cost on every run, so the talking-head path has a ceiling (bytes).
READ_BUDGET = {"start": 12000, "cut": 15000, "style-edit": 25000, "product-video": 30000, "logo-pack": 7000, "skill-improver": 7500, "skill-maker": 9000}
READ_FIRST = re.compile(r"[Rr]ead \**`([^`]+)`\**:?\s+first")


def required_reads(skill_md):
    """SKILL.md and the files it marks "read first", resolved against the skill and plugin folders."""
    text = skill_md.read_text(encoding="utf-8")
    plugin = skill_md.parents[2]
    files = [skill_md]
    for ref in READ_FIRST.findall(text):
        ref = ref.replace("${KIROCUT_PLUGIN}", str(plugin)).replace("${KIROCUT_SKILL}", str(skill_md.parent))
        files.append(Path(ref) if Path(ref).is_absolute() else skill_md.parent / ref)
    return files


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        errors.append(f"{path}: no frontmatter")
        return {}, text
    head, body = text[4:].split("\n---\n", 1)
    # ponytail: one `key: value` per line is all these files use; nested YAML would need a real parser
    fm = dict(line.split(":", 1) for line in head.splitlines() if re.match(r"^[A-Za-z-]+:", line))
    return {k.strip(): v.strip() for k, v in fm.items()}, body


MAX_LINES = 250
TRIGGERS = {}  # quoted trigger phrase -> skill that claims it


def check_skill(path):
    fm, body = frontmatter(path)
    vendored = (path.parent / "LICENSE").exists()
    # PRINCIPLES.md "Cost": a skill is read every time it fires; detail goes in references/
    lines = path.read_text(encoding="utf-8").count("\n")
    if not vendored and lines > MAX_LINES:
        errors.append(f"{path}: {lines} lines, over {MAX_LINES}; move detail into references/")
    # Two skills claiming the same quoted phrase both fire on it. Phrases after "Not for" are disclaimers.
    claims = re.split(r"\bnot for\b", fm.get("description", ""), flags=re.I)[0]
    for phrase in re.findall(r'"([^"]{3,})"', claims):
        key = re.sub(r"\s+", " ", phrase.lower().strip(" .,"))
        other = TRIGGERS.setdefault(key, path.parent.name)
        if other != path.parent.name:
            errors.append(f"{path}: trigger \"{phrase}\" is also claimed by {other}; give it to one skill")
    name = fm.get("name", "")
    if not NAME.match(name) or len(name) > 64 or name != path.parent.name:
        errors.append(f"{path}: name {name!r} must be kebab-case, at most 64 chars, and match its folder")
    if not 0 < len(fm.get("description", "")) <= 1024:
        errors.append(f"{path}: description must be 1-1024 chars (is {len(fm.get('description', ''))})")
    if not fm.get("license"):
        errors.append(f"{path}: no license")
    if not 0 < len(fm.get("compatibility", "")) <= 500:
        errors.append(f"{path}: compatibility must be 1-500 chars")
    if PATHS_LINE not in body:
        errors.append(f"{path}: missing the line {PATHS_LINE!r}")
    # every question goes in the question box (PRINCIPLES.md "Asking"); vendored skills keep their own text
    if not vendored and "kirocut_ask" not in body:
        errors.append(f"{path}: never says to ask in the question box (kirocut_ask)")
    for ref in re.findall(r"\$\{KIROCUT_SKILL\}/((?:references|scripts)/[\w./-]+)", body):
        if not (path.parent / ref).exists():
            errors.append(f"{path}: points at {ref}, which does not exist")
    # PRINCIPLES.md "Speed": a skill that hands work to an agent names one that ships, with its model and tools set
    agents = path.parents[2] / "agents"
    for ref in set(re.findall(r"agents/([\w-]+)\.md", body) + re.findall(r"`([a-z]+(?:-[a-z]+)+)(?:\.md)?` agents?\b", body)):
        fm_a = frontmatter(agents / f"{ref}.md")[0] if (agents / f"{ref}.md").exists() else None
        if fm_a is None:
            errors.append(f"{path}: names the agent {ref}, but {agents / (ref + '.md')} does not exist")
        elif not fm_a.get("tools"):
            errors.append(f"{agents / (ref + '.md')}: {path.parent.name} launches it, so it needs tools set")


def check_body(path):
    """Runs after every skill's triggers are in TRIGGERS."""
    _, body = frontmatter(path)
    # Quoting another skill's trigger without naming that skill acts on a request the router sends elsewhere.
    for m in re.finditer(r'"([^"]{3,80})"', body):
        key = re.sub(r"\s+", " ", m.group(1).lower().strip(" .,"))
        lines = body[body.rfind("\n", 0, m.start()) + 1:body.find("\n", m.end())]
        for phrase, owner in TRIGGERS.items():
            if owner != path.parent.name and (key == phrase or key.startswith(phrase + " ")) and not re.search(rf"\b{owner}\b", lines):
                errors.append(f"{path}: quotes \"{key}\", which routes to {owner}; name {owner} or drop it")
    # A `python3 "<script>"` command (not the run.py launcher) needs the Windows line the other skills have.
    if re.search(r'python3 "[^"\n]*(?<!run\.py)"', body) and not re.search(r"`python3`[^.]*`py`|`py`[^.]*`python3`", body):
        errors.append(f"{path}: runs `python3` with no line saying `py` on Windows")


def check_agent(path):
    fm, _ = frontmatter(path)
    for key in ("name", "description", "tools"):
        if not fm.get(key):
            errors.append(f"{path}: no {key}")
    tools = re.findall(r'[A-Za-z@_/*-]+', fm.get("tools", "").strip("[]"))   # Kiro's tool categories (docs/KIRO-COMPAT.md), or @server selectors
    for t in tools:
        if t not in ("read", "write", "shell", "web", "spec") and not t.startswith("@"):
            errors.append(f"{path}: tool {t!r} is not a Kiro tool category (read, write, shell, web, spec) or an @server selector")
    if fm.get("includeMcpJson") != "true":
        errors.append(f"{path}: includeMcpJson must be true so the agent can call the kirocut tools")
    if fm.get("name") != path.stem:
        errors.append(f"{path}: name {fm.get('name')!r} must match the file name")
    # An agent prompt is not a skill: ${KIROCUT_PLUGIN} and ${KIROCUT_SKILL} may reach it unexpanded.
    if "${KIROCUT_" in path.read_text(encoding="utf-8"):
        errors.append(f"{path}: uses a ${{KIROCUT_...}} path, which may not expand in an agent; have the caller pass the path")


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        errors.append(f"{path}: {e}")
        return {}



def text_calls_without_utf8(src):
    """Line numbers of read_text / write_text / text-mode open() or os.fdopen() with no encoding. Windows reads
    those as cp1252, so a curly quote or an accented name in a transcript breaks the script there."""
    def mode(c):
        m = c.args[1] if len(c.args) > 1 else next((k.value for k in c.keywords if k.arg == "mode"), None)
        return "r" if m is None else (m.value if isinstance(m, ast.Constant) and isinstance(m.value, str) else None)
    out = []
    for c in ast.walk(ast.parse(src)):
        if not isinstance(c, ast.Call) or any(k.arg in ("encoding", None) for k in c.keywords):
            continue
        f = c.func
        if isinstance(f, ast.Attribute) and f.attr in ("read_text", "write_text"):
            out.append(c.lineno)
        elif (isinstance(f, ast.Name) and f.id == "open") or (isinstance(f, ast.Attribute) and f.attr == "fdopen"):
            m = mode(c)
            if m is not None and "b" not in m:
                out.append(c.lineno)
    return out


_O = "cl" + "aude"
# another agent's name, tool, settings folder, env var, CLI package or internal names built on it
OTHER = re.compile(r"\bCl" + r"aude\b|\$\{CL" + r"AUDE_|\bCL" + r"AUDE_\w+|AskUser" + r"Question|\." + _O + r"\b|\b" + _O + r"_\w+|\w+_" + _O
                   + r"\b|/" + _O + r"\b|ANTHROPIC_\w+|@anthrop" + "ic-ai/")


# a product named in the sample take and in examples (its logo, a counter "faster than <it>", a word heard as "cloud"): data, not our agent
SAMPLE = re.compile("|".join([r"names Jev and Cl" + "aude", r"\"name\": \"Cl" + "aude\"", r"Cl" + "aude interface palette",
                              r"\"cloud\": \"Cl" + "aude\"", r"Cl" + r"aude.s$", r"\"word\": \"Cl" + "aude\"", r"ok +Cl" + "aude +images/",
                              r"faster than Cl" + "aude", r"\"names\": \[\"Cl" + r"aude\"\]", r"\bJev\b", r"models like Cl" + "aude",
                              r"cloud=Cl" + "aude", r"\"cloud\", \"Cl" + "aude\"", r"\"find\": \"Cl" + "aude\"", r"github\.com/anthropics/"]))
# lines in a script's demo that quote the sample's words as data ("... send it to <it>", its captions)
QUOTED = re.compile(r"[\"'][^\"'\n]*\bCl" + r"aude\b[^\"'\n]*[\"']")
# the one module that names the old agent on purpose: it renames an older edit's files and keys once
OLD_NAMES = ("legacy.py",)


def check_published():
    """What a public copy of the repo needs: an open-source licence GitHub detects at the root, and .kiro/ (steering,
    specs, hooks, agents) committed, never ignored."""
    lic = ROOT / "LICENSE"
    if not lic.is_file() or not lic.read_text(encoding="utf-8").startswith("MIT License"):
        errors.append("LICENSE: missing or not the MIT licence at the repo root")
    for n, ln in enumerate((ROOT / ".gitignore").read_text(encoding="utf-8").splitlines(), 1):
        pat = ln.strip().lstrip("/").rstrip("/")
        if pat and not pat.startswith("#") and (pat == ".kiro" or pat.startswith(".kiro/") or pat in (".*", "*")):
            errors.append(f".gitignore:{n}: ignores {ln.strip()!r}; .kiro/ must stay in the repo")
    for need in ("steering", "specs", "hooks", "agents", "skills"):
        if not any((ROOT / ".kiro" / need).iterdir() if (ROOT / ".kiro" / need).is_dir() else []):
            errors.append(f".kiro/{need}/ is missing or empty")


def check_no_other_agent():
    """What the user reads and what the agent is told say Kiro, and ask through kirocut_ask. Skill and reference text, the steering,
    the window's pages and the editor's own scripts are checked; sample data (a creator's or a product's name in a transcript)
    and CHANGELOG.md, which says what changed, are not."""
    pats = ["README.md", "AGENTS.md", "GEMINI.md", ".kiro/steering/*.md", ".kiro/hooks/*.json", "docs/*.md", "docs/spike/*.py", "docs/spike/*.md",
            "plugins/*/skills/*/SKILL.md", "plugins/*/skills/*/references/*.md", "plugins/*/agents/*.md", "plugins/kirocut/PRINCIPLES.md",
            "plugins/kirocut/evals/*/prompt.md", "plugins/kirocut/evals/*/graders/*.md", "plugins/style-match/evals/*/prompt.md",
            "plugins/style-match/evals/*/graders/*.md", "plugins/kirocut/mcp/*", "extensions/**/*.js", "extensions/**/*.md",
            "plugins/kirocut/lib/kirocut/*.py", "plugins/kirocut/lib/kirocut/*.js", "plugins/kirocut/lib/kirocut/*.html",
            "plugins/kirocut/lib/kirocut/*.md", "plugins/style-match/skills/style-match/scripts/_progress.py",
            "plugins/kirocut/skills/setup/scripts/setup.py", "plugins/kirocut/skills/update/scripts/update.py",
            "plugins/kirocut/skills/skill-maker/scripts/skill_maker.py", "tests/*.py", "tests/*.mjs", "tests/*.txt",
            "plugins/*/skills/*/scripts/*.py", "plugins/*/skills/*/scripts/*.mjs", "plugins/kirocut/remotion/src/**/*.ts*",
            "plugins/kirocut/preview/*.ts*", ".github/workflows/*.yml", ".gitignore", "RELEASING.md", "tests/*.sh"]
    for pat in pats:
        for f in sorted(set(ROOT.glob(pat))):
            if f.name in OLD_NAMES or "_port" in f.parts:
                continue
            if not f.is_file() or "__pycache__" in f.parts or f.suffix in (".pyc", ".json") and f.parent.name != "hooks":
                continue
            script = "scripts" in f.parts
            for n, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                m = OTHER.search(ln)
                if m and not SAMPLE.search(ln) and not (script and QUOTED.search(ln) and m.group() == "Cl" + "aude"):
                    errors.append(f"{f.relative_to(ROOT).as_posix()}:{n}: says {m.group()!r}; this editor runs in Kiro (kirocut_ask, Kiro, ${{KIROCUT_PLUGIN}})")
                    break


SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
POWERS = ("plugins/kirocut", "plugins/style-match")


def main():
    versions = {}
    for rel in POWERS:
        plugin = ROOT / rel
        manifest = load(plugin / "plugin.json")
        if manifest.get("$schema") != SCHEMA:
            errors.append(f"{rel}/plugin.json: $schema must be the Agent Plugins schema")
        for key in ("name", "version", "description", "keywords"):
            if not manifest.get(key):
                errors.append(f"{rel}/plugin.json: missing {key}")
        if not (manifest.get("author") or {}).get("name"):
            errors.append(f"{rel}/plugin.json: author.name is required")
        versions[manifest.get("name")] = manifest.get("version")
        found = list(plugin.glob("skills/*/SKILL.md"))
        if not found:
            errors.append(f"{rel}: no skills")
        for skill in found:
            check_skill(skill)
            check_body(skill)
            wrap = ROOT / ".kiro" / "skills" / skill.parent.name / "SKILL.md"
            if not wrap.is_file():
                errors.append(f".kiro/skills/{skill.parent.name}: missing, so opening the folder does not load this skill")
            elif f"name: {skill.parent.name}" not in wrap.read_text(encoding="utf-8"):
                errors.append(f".kiro/skills/{skill.parent.name}: name does not match the skill")
        for agent in plugin.glob("agents/*.md"):
            check_agent(agent)
        if (plugin / "hooks" / "hooks.json").exists():
            load(plugin / "hooks" / "hooks.json")
    check_no_other_agent()
    check_published()
    sys.path.insert(0, str(ROOT / "tests"))
    import sync_kiro
    errors.extend(f"{rel}: out of step with plugins/; run python3 tests/sync_kiro.py" for rel in sync_kiro.drift())
    if len(set(versions.values())) != 1:
        errors.append(f"plugin versions differ: {versions}")
    for extra in (".codex-plugin/plugin.json", ".cursor-plugin/plugin.json"):
        path = ROOT / extra
        if not path.is_file():
            continue
        for s in load(path).get("skills", []):
            if not (ROOT / s).is_dir():
                errors.append(f"{extra}: skills path {s} does not exist")

    # Opening the repo in Kiro loads the editor from this folder (README "Start here", Way 1).
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for path in ("Way 1: open this folder in Kiro", "kiro-cli powers install"):
        if path not in readme:
            errors.append(f"README.md: lost the start path {path!r}")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    if "plugins/kirocut/skills/start/SKILL.md" not in agents[:600]:
        errors.append("AGENTS.md: the first lines must send an agent to the start skill")
    if agents != (ROOT / "GEMINI.md").read_text(encoding="utf-8"):
        errors.append("GEMINI.md: differs from AGENTS.md; copy it across")

    # Setup links straight to each key's page (PRINCIPLES.md "Asking"), so nobody hunts for it.
    setup = (ROOT / "plugins/kirocut/skills/setup/SKILL.md").read_text(encoding="utf-8")
    for url in KEY_URLS:
        if url not in setup:
            errors.append(f"plugins/kirocut/skills/setup/SKILL.md: lost the direct key link {url}")

    # The rules only an agent can follow are proven by evals (docs/feedback-matrix.md); they must not vanish.
    for case, grader in EVALS:
        d = ROOT / case
        if not (d / "prompt.md").exists() or not any(grader in g.read_text(encoding="utf-8") for g in d.glob("graders/*.md")):
            errors.append(f"{case}: missing, or no grader with {grader!r}")

    # The style.json contract is copied into style-match so it ships with that plugin.
    def section(p):
        t = p.read_text(encoding="utf-8")
        return t[t.index("## style.json"):].split("\n## ", 1)[0].strip()
    a = ROOT / "plugins/kirocut/skills/style-edit/references/contracts.md"
    b = ROOT / "plugins/style-match/skills/style-match/references/contracts.md"
    if section(a) != section(b):
        errors.append(f"{b}: style.json section differs from {a}; copy it across")

    # style-match ships kirocut's pins for what it installs, so its fix lines never go unpinned.
    sys.path.insert(0, str(ROOT / "plugins/kirocut/lib"))
    from kirocut import lock
    if not lock.TEARDOWN_LOCK.exists() or lock.TEARDOWN_LOCK.read_text(encoding="utf-8") != lock.subset(lock.TEARDOWN_ROOTS):
        errors.append(f"{lock.TEARDOWN_LOCK}: out of sync with requirements.lock; "
                      "run python3 plugins/kirocut/lib/kirocut/lock.py teardown")

    for p in ROOT.rglob("*"):
        # Vendored third-party skills (their own LICENSE file next to SKILL.md) stay verbatim.
        vendored = any((q / "LICENSE").exists() and (q / "SKILL.md").exists() for q in p.parents)
        if p.suffix in (".md", ".json", ".py", ".yml") and "node_modules" not in p.parts and ".git" not in p.parts and not vendored and "results" not in p.parts:
            if chr(0x2014) in p.read_text(encoding="utf-8", errors="ignore"):
                errors.append(f"{p}: contains an em dash")


    # Personal names and test-file names never ship. Stored as hashes so this file does not name them.
    import hashlib
    PRIVATE = {'8e3c16abe7053e2a', '73ea4d074e1e099e', '34517c83d2a1c75c', 'f2486dfd64f3a9a7', 'f68d9243b3f95c38', 'aef9b0cbd5d5c214', '9ba138bfd348ae5e', '085caa96e51d45cd', 'a4ba610f97acea14', '97599235748ff4a0', 'f5f9cc117d31860b'}
    REFERRAL = {'527a778497bd1a9c'}
    for p in ROOT.rglob("*"):
        if p.suffix not in (".md", ".json", ".py", ".mjs", ".ts", ".tsx", ".yml") or "node_modules" in p.parts or ".git" in p.parts or p.name.endswith("lock.json"):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        # Nothing pipes a downloaded script into a shell (Kiro's own installer excepted).
        if re.search(r"\b(curl|wget)\b(?![^\n]*cli\.kiro\.dev/install)[^\n|]*\|\s*(sudo\s+(-\S+\s+)*)?(ba|z)?sh\b", text):
            errors.append(f"{p}: pipes a downloaded script into a shell; use the vendor's signed package steps")
        # A rendered family never resolves to system-ui alone: it is SF Pro on a Mac and another font on
        # the Linux render machines (Modal, GitHub Actions, Lambda), so the stills and the render differ.
        if p.suffix == ".tsx" and re.search(r"""(resolve\(|null : )\s*["'`]system-ui""", text):
            errors.append(f"{p}: a font falls back to system-ui alone; fall back to a Google font every renderer loads")
        if re.search(r"\bIMG[-_](?!1234\b)\d{4}\b", text, re.I):
            errors.append(f"{p}: names a personal test file (IMG_####); say 'the sample take'")
        # The one shipped referral link (post.py's Zernio sign-up), allowed by its hash, never a name on its own
        text = re.sub(r"https://zernio\.link/[\w-]+", lambda m: "" if hashlib.sha256(m.group().encode()).hexdigest()[:16] in REFERRAL else m.group(), text)
        for w in set(re.findall(r"[a-z0-9]{4,}", text.lower())):
            if hashlib.sha256(w.encode()).hexdigest()[:16] in PRIVATE:
                errors.append(f"{p}: contains a private name; keep public files generic")
                break

    # Skills run scripts through run.py, which finds the venv under KIROCUT_HOME; a hardcoded home
    # path ignores it, and %USERPROFILE% does not expand in Git Bash.
    for p in [*ROOT.glob("plugins/*/skills/*/SKILL.md"), *ROOT.glob("plugins/*/skills/*/references/*.md"),
              *ROOT.glob("plugins/*/agents/*.md")]:
        if re.search(r"~/\.kirocut/venv|%USERPROFILE%", p.read_text(encoding="utf-8")):
            errors.append(f"{p}: hardcodes the venv path; run scripts with lib/kirocut/run.py")
    run_a = ROOT / "plugins/kirocut/lib/kirocut/run.py"
    run_b = ROOT / "plugins/style-match/skills/style-match/scripts/run.py"
    if run_a.read_bytes() != run_b.read_bytes():
        errors.append(f"{run_b}: differs from {run_a}; copy it across")
    prog_a = ROOT / "plugins/kirocut/lib/kirocut/progress.py"
    prog_b = ROOT / "plugins/style-match/skills/style-match/scripts/_progress.py"
    if prog_a.read_bytes() != prog_b.read_bytes():
        errors.append(f"{prog_b}: differs from {prog_a}; copy it across")
    # The certificate fallback is copied into style-match, which cannot import kirocut.
    def ctx_fn(p):
        t = p.read_text(encoding="utf-8")
        return t[t.index("def context():"):].split("\ndef ", 1)[0]
    net_a = ROOT / "plugins/kirocut/lib/kirocut/net.py"
    net_b = ROOT / "plugins/style-match/skills/style-match/scripts/_net.py"
    if ctx_fn(net_a) != ctx_fn(net_b) or "FIX = " not in net_b.read_text(encoding="utf-8"):
        errors.append(f"{net_b}: context() differs from {net_a}; copy it across")

    for name, budget in READ_BUDGET.items():
        files = required_reads(ROOT / "plugins/kirocut/skills" / name / "SKILL.md")
        missing = [str(f) for f in files if not f.exists()]
        size = lambda f: len(f.read_bytes().replace(b"\r\n", b"\n"))   # a Windows checkout has CRLF: count the file as git stores it
        total = sum(size(f) for f in files if f.exists())
        if missing or total > budget:
            errors.append(f"{name}: required reads {total} bytes (budget {budget}): "
                          + ", ".join(f"{f.name} {size(f)}" if f.exists() else f"{f} missing" for f in files))

    for py in sorted(ROOT.glob("plugins/**/*.py")) + sorted(ROOT.glob("tests/*.py")):
        if "node_modules" in py.parts:
            continue
        for ln in text_calls_without_utf8(py.read_text(encoding="utf-8")):
            errors.append(f"{py.relative_to(ROOT)}:{ln}: text file read or written without encoding=\"utf-8\" (breaks on Windows)")
    assert text_calls_without_utf8('open("a")\nPath("b").read_text()\nopen("c", "rb")\nopen("d", encoding="utf-8")') == [1, 2]

    for e in errors:
        print("FAIL", e)
    print("plugins ok" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
