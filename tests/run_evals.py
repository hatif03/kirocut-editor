#!/usr/bin/env python3
"""Runs the eval cases (plugins/<plugin>/evals/<case>/prompt.md and graders/*.md) through the Kiro CLI, headless.

    py tests/run_evals.py                          # 3 runs per case, both plugins
    py tests/run_evals.py --runs 1 --case start-asks
    py tests/run_evals.py demo                     # self-check: parses every case, grades canned runs, no model calls

Real model calls: needs `kiro-cli` on PATH (or KIROCUT_KIRO_CLI) and a login or KIRO_API_KEY (Kiro CLI headless mode).
Each run is `kiro-cli chat --v3 --no-interactive --output-format stream-json --trust-tools=<the case's tools> <text>`
from the repo root, so the workspace's .kiro steering, skills and agents load as they do in the IDE. The text is the
case's dry_run note and then its prompt. Only the case's tools are trusted, so a shell or file edit is denied.

prompt.md frontmatter: `tools` (Kiro CLI tool names or @server/tool), `dry_run` (the note before the prompt).
Graders (frontmatter, the llm rubric in the body):
  skill_used  skill: <name> | [a, b] | any; min (default 1), max: the run read that skill's SKILL.md (or skill::<name>)
  agent_used  agent: <name>: the run started that sub-agent
  regex       pattern, flags: i, target: reply (default) or trace
  llm         a second headless run with no tools grades the rubric; focus: reply (default) or trace
A run passes when every grader passes; a case scores its passing runs over its runs. Results go to
eval-results/<plugin>.json and .html (EVAL_OUT). Exit 1 when a case scores under --threshold (EVAL_THRESHOLD, 0.8).
EVAL_MODEL and EVAL_JUDGE_MODEL pin the models; EVAL_TIMEOUT is the seconds per run (600).
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ("style-match", "kirocut")
TYPES = ("skill_used", "agent_used", "regex", "llm")


# ---------------------------------------------------------------- cases
def scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if len(v) >= 2 and v[0] == v[-1] == '"':
        return json.loads(v)
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    return int(v) if re.fullmatch(r"-?\d+", v) else v


def front(text):
    """(frontmatter dict, body) of a prompt or grader file: scalars, 'quoted', "quoted", [lists] and | blocks."""
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n?(.*)", text, re.S)
    if not m:
        return {}, text.strip()
    meta, lines, i = {}, m.group(1).splitlines(), 0
    while i < len(lines):
        k, _, v = lines[i].partition(":")
        i += 1
        if not k.strip():
            continue
        if v.strip() in ("|", "|-", ">"):
            block = []
            while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                block.append(lines[i].strip() if v.strip() == ">" else lines[i][2:])
                i += 1
            meta[k.strip()] = (" " if v.strip() == ">" else "\n").join(block).strip()
        else:
            meta[k.strip()] = scalar(v)
    return meta, m.group(2).strip()


def cases(plugin=None, only=None):
    out = []
    for p in PLUGINS:
        if plugin and p != plugin:
            continue
        for f in sorted((ROOT / "plugins" / p / "evals").glob("*/prompt.md")):
            if only and only not in f.parent.name:
                continue
            meta, prompt = front(f.read_text(encoding="utf-8"))
            graders = []
            for g in sorted((f.parent / "graders").glob("*.md")):
                gm, body = front(g.read_text(encoding="utf-8"))
                graders.append({**gm, "name": g.stem, "rubric": body})
            out.append({"plugin": p, "case": f.parent.name, "tools": meta.get("tools") or [], "dry_run": meta.get("dry_run") or "",
                        "prompt": prompt, "graders": graders})
    return out


# ---------------------------------------------------------------- one run
def cli():
    return shutil.which(os.environ.get("KIROCUT_KIRO_CLI") or "kiro-cli")


def command(case, exe="kiro-cli", model=None):
    cmd = [exe, "chat", "--v3", "--no-interactive", "--output-format", "stream-json"]
    if case["tools"]:
        cmd.append("--trust-tools=" + ",".join(case["tools"]))
    if model:
        cmd += ["--model", model]
    text = (f"[Eval setup, not from the user] {case['dry_run']}\n\n" if case["dry_run"] else "") + case["prompt"]
    return cmd + [text]


IN_KEYS = ("input", "args", "arguments", "params", "toolInput", "tool_input")
NAME_KEYS = ("name", "toolName", "tool_name", "tool", "toolId")


def parse_stream(out):
    """What a stream-json run did: {reply, calls: [(tool, input as JSON text)]}. Lines that are not JSON are reply text,
    so a plain-text run still grades."""
    calls, chunks, plain = [], [], []

    def walk(x, in_call=False):
        if isinstance(x, dict):
            name = next((x[k] for k in NAME_KEYS if isinstance(x.get(k), str)), None)
            arg = next((x[k] for k in IN_KEYS if k in x), None)
            if name and arg is not None:
                calls.append((name, arg if isinstance(arg, str) else json.dumps(arg)))
                in_call = True
            for k, v in x.items():
                if not in_call and k in ("text", "delta", "content") and isinstance(v, str):
                    chunks.append(v)
                else:
                    walk(v, in_call or k in IN_KEYS)
        elif isinstance(x, list):
            for v in x:
                walk(v, in_call)

    for ln in out.splitlines():
        try:
            walk(json.loads(ln))
        except ValueError:
            plain.append(ln)
    reply = "".join(chunks) + ("\n" if chunks and plain else "") + "\n".join(plain)
    return {"reply": reply.strip(), "calls": calls}


def trace(run):
    return run["reply"] + "".join(f"\n[tool] {n} {i}" for n, i in run["calls"])


def skill_hits(run, names):
    pat = "|".join(re.escape(n) for n in names) if names != ["any"] else r"[\w-]+"
    rx = re.compile(rf"skills[/\\]+(?:{pat})[/\\]+SKILL\.md|skill::(?:{pat})\b|\"skill\"\s*:\s*\"(?:[\w-]+:)?(?:{pat})\"")
    return sum(1 for _, i in run["calls"] if rx.search(i))


def judge_with_cli(prompt, exe, model=None):
    cmd = [exe, "chat", "--v3", "--no-interactive"] + (["--model", model] if model else []) + [prompt]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT,
                       timeout=int(os.environ.get("EVAL_TIMEOUT") or 600))
    return r.stdout


def grade(g, run, judge):
    """(passed, why) for one grader on one run. judge(prompt) -> the judge's text."""
    t = g.get("type")
    if t == "skill_used":
        names = g["skill"] if isinstance(g["skill"], list) else [g["skill"]]
        n, hi = skill_hits(run, names), g.get("max")
        lo = g.get("min", 0 if hi == 0 else 1)
        ok = n >= lo and (hi is None or n <= hi)
        return ok, f"read {'/'.join(names)} {n} time(s)"
    if t == "agent_used":
        a = re.escape(g["agent"])
        rx = re.compile(rf"\"(?:agent|agent_name|name|subagent|subagent_type)\"\s*:\s*\"(?:kirocut:)?{a}\"")
        ok = any(rx.search(i) or re.search("agent", n, re.I) and re.search(rf"\b{a}\b", i) for n, i in run["calls"])
        return ok, f"{'started' if ok else 'never started'} {g['agent']}"
    if t == "regex":
        text = trace(run) if g.get("target") == "trace" else run["reply"]
        ok = re.search(g["pattern"], text, re.I if "i" in str(g.get("flags", "")) else 0) is not None
        return ok, f"/{g['pattern']}/ {'found' if ok else 'not found'}"
    if t == "llm":
        focus = "trace" if g.get("focus") == "trace" else "reply"
        text = trace(run) if focus == "trace" else run["reply"]
        out = judge("You grade one run of an AI agent (Kiro) against a rubric. Do not use any tools. Answer PASS or FAIL "
                    f"on the first line, then one sentence why.\n\nRubric:\n{g['rubric']}\n\nThe run's {focus}:\n<<<\n{text}\n>>>")
        m = re.search(r"\b(PASS|FAIL)\b", out or "")
        return bool(m and m.group(1) == "PASS"), (out or "no answer").strip().splitlines()[-1][:200] if out else "no answer"
    return False, f"unknown grader type {t!r}"


def run_case(case, runs, exe, model, judge_model):
    judge = lambda p: judge_with_cli(p, exe, judge_model)   # noqa: E731
    res = []
    for _ in range(runs):
        try:
            r = subprocess.run(command(case, exe, model), capture_output=True, text=True, encoding="utf-8", errors="replace",
                               cwd=ROOT, timeout=int(os.environ.get("EVAL_TIMEOUT") or 600))
            run, err = parse_stream(r.stdout), r.stderr[-2000:] if r.returncode else ""
        except subprocess.TimeoutExpired:
            run, err = {"reply": "", "calls": []}, "timed out"
        gs = [{"grader": g["name"], **dict(zip(("pass", "why"), grade(g, run, judge)))} for g in case["graders"]]
        res.append({"pass": not err and all(g["pass"] for g in gs), "graders": gs, "reply": run["reply"][-4000:],
                    "calls": [n for n, _ in run["calls"]], "error": err})
    score = sum(r["pass"] for r in res) / max(1, len(res))
    print(f"{case['plugin']}/{case['case']}: {score:.2f}", flush=True)
    return {"case": case["case"], "score": score, "runs": res}


def write(out, plugin, results):
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{plugin}.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    rows = []
    for c in results:
        for i, r in enumerate(c["runs"], 1):
            gs = "<br>".join(f"{'PASS' if g['pass'] else 'FAIL'} {html.escape(g['grader'])}: {html.escape(g['why'])}" for g in r["graders"])
            rows.append(f"<tr><td>{html.escape(c['case'])}</td><td>{i}</td><td>{c['score']:.2f}</td><td>{gs}</td>"
                        f"<td><pre>{html.escape(r['error'] or r['reply'][-1500:])}</pre></td></tr>")
    (out / f"{plugin}.html").write_text(
        f"<!doctype html><meta charset=utf-8><title>KiroCut evals: {plugin}</title><style>body{{font:14px system-ui}}td{{vertical-align:top;"
        f"border-top:1px solid #ccc;padding:4px}}pre{{white-space:pre-wrap;max-width:60ch}}</style><h1>{plugin}</h1><table>"
        "<tr><th>case</th><th>run</th><th>score</th><th>graders</th><th>reply</th></tr>" + "".join(rows) + "</table>", encoding="utf-8")


def main(argv):
    ap = argparse.ArgumentParser(description="Run the eval cases through the Kiro CLI")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--case", default=None, help="only cases whose folder name contains this")
    ap.add_argument("--plugin", choices=PLUGINS, default=None)
    ap.add_argument("-j", type=int, default=4, help="cases at once")
    ap.add_argument("--threshold", type=float, default=float(os.environ.get("EVAL_THRESHOLD") or 0.8))
    a = ap.parse_args(argv)
    exe = cli()
    if not exe:
        sys.exit("kiro-cli is not on PATH: install the Kiro CLI (kiro.dev/docs/cli), sign in or set KIRO_API_KEY, then run again")
    todo = cases(a.plugin, a.case)
    if not todo:
        sys.exit("no eval case matches")
    model, judge_model = os.environ.get("EVAL_MODEL"), os.environ.get("EVAL_JUDGE_MODEL")
    with ThreadPoolExecutor(max(1, a.j)) as ex:
        done = list(ex.map(lambda c: (c["plugin"], run_case(c, a.runs, exe, model, judge_model)), todo))
    out, low = Path(os.environ.get("EVAL_OUT") or ROOT / "eval-results"), []
    for p in PLUGINS:
        res = [r for q, r in done if q == p]
        if res:
            write(out, p, res)
        low += [f"{p}/{r['case']} {r['score']:.2f}" for r in res if r["score"] < a.threshold]
    print(f"results in {out}")
    if low:
        print("under the threshold: " + ", ".join(low))
        return 1
    return 0


# ---------------------------------------------------------------- self-check
def demo():
    import tempfile
    all_cases = cases()
    assert len(all_cases) >= 20, len(all_cases)
    skills = {p.parent.name for p in ROOT.glob("plugins/*/skills/*/SKILL.md")}
    agents = {p.stem for p in ROOT.glob("plugins/kirocut/agents/*.md")}
    for c in all_cases:
        where = f"{c['plugin']}/{c['case']}"
        assert c["prompt"] and c["graders"], f"{where}: a prompt and at least one grader"
        assert isinstance(c["tools"], list) and c["tools"], f"{where}: tools lists what the run may use"
        assert not {"execute_bash", "shell", "write", "fs_write", "execute_pwsh"} & set(c["tools"]), f"{where}: a dry run has no shell or edits"
        for g in c["graders"]:
            assert g.get("type") in TYPES, f"{where}/{g['name']}: type {g.get('type')!r}"
            if g["type"] == "skill_used":
                for n in g["skill"] if isinstance(g["skill"], list) else [g["skill"]]:
                    assert n == "any" or n in skills, f"{where}/{g['name']}: no skill {n!r}"
            if g["type"] == "agent_used":
                assert g["agent"] in agents, f"{where}/{g['name']}: no agent {g['agent']!r}"
            if g["type"] == "regex":
                re.compile(g["pattern"])
            if g["type"] == "llm":
                assert "PASS" in g["rubric"] and "FAIL" in g["rubric"], f"{where}/{g['name']}: the rubric says PASS and FAIL"
    cut = next(c for c in all_cases if c["case"] == "cut-my-video")
    cmd = command(cut)
    assert cmd[:5] == ["kiro-cli", "chat", "--v3", "--no-interactive", "--output-format"] and "--trust-tools=read,glob,grep,@kirocut/kirocut_ask" in cmd
    assert cmd[-1].startswith("[Eval setup, not from the user] Eval dry run") and cmd[-1].endswith("cut my video, it's at ./raw-take.mov")
    print("cases    ok: %d cases parse, every grader names a real skill or agent, no shell or edit tools" % len(all_cases))

    # a stream-json run: text chunks, a skill read, a sub-agent, then a plain line
    lines = [{"type": "assistantText", "text": "I'll cut first, "}, {"type": "assistantText", "delta": "then style it."},
             {"type": "toolUse", "toolUse": {"name": "read_file", "input": {"path": ".kiro/skills/cut/SKILL.md"}}},
             {"type": "toolUse", "name": "use_subagent", "args": {"agent_name": "clip-editor", "text": "edit clip 1"}}]
    run = parse_stream("\n".join(json.dumps(x) for x in lines) + "\nWhich do you want: 1) cut only 2) everything?")
    assert run["reply"].startswith("I'll cut first, then style it.") and run["reply"].endswith("everything?"), run["reply"]
    assert [n for n, _ in run["calls"]] == ["read_file", "use_subagent"] and "clip-editor" not in run["reply"], run
    no = lambda p: "FAIL"   # noqa: E731
    assert grade({"type": "skill_used", "skill": "cut"}, run, no)[0]
    assert not grade({"type": "skill_used", "skill": "start"}, run, no)[0]
    assert grade({"type": "skill_used", "skill": ["start", "cut"]}, run, no)[0]
    assert not grade({"type": "skill_used", "skill": "any", "max": 0}, run, no)[0], "a skill read fails no-skill"
    assert grade({"type": "skill_used", "skill": "any", "max": 0}, {"reply": "def f(): pass", "calls": []}, no)[0]
    assert grade({"type": "agent_used", "agent": "clip-editor"}, run, no)[0]
    assert not grade({"type": "agent_used", "agent": "cut-judge"}, run, no)[0]
    assert grade({"type": "regex", "pattern": "cut first|in one go", "flags": "i", "target": "trace"}, run, no)[0]
    assert not grade({"type": "regex", "pattern": "SKILL\\.md"}, run, no)[0], "the reply alone has no tool input"
    assert grade({"type": "regex", "pattern": "SKILL\\.md", "target": "trace"}, run, no)[0]
    asked = []
    ok, why = grade({"type": "llm", "rubric": "PASS if it asks. FAIL if not.", "focus": "trace"}, run,
                    lambda p: asked.append(p) or "PASS\nit asks with two choices")
    assert ok and why == "it asks with two choices" and "[tool] read_file" in asked[0] and "PASS if it asks" in asked[0]
    assert not grade({"type": "llm", "rubric": "x"}, run, lambda p: "**FAIL**: nothing asked")[0]
    print("graders  ok: stream-json parsed (text, tool calls, plain lines), skill/agent/regex/llm grading")

    m, body = front("---\ntype: regex\npattern: 'it''s|a,b'\nflags: i\nlist: [read, \"@kirocut/kirocut_ask\"]\nn: 0\n"
                    "dry_run: |\n  line one\n  line two\n---\nbody text\n")
    assert m == {"type": "regex", "pattern": "it's|a,b", "flags": "i", "list": ["read", "@kirocut/kirocut_ask"], "n": 0,
                 "dry_run": "line one\nline two"} and body == "body text", m
    with tempfile.TemporaryDirectory() as d:
        write(Path(d), "kirocut", [{"case": "x<y", "score": 0.5, "runs": [{"pass": False, "graders": [{"grader": "g", "pass": False, "why": "no"}],
                                                                          "reply": "<b>", "calls": [], "error": ""}]}])
        page = (Path(d) / "kirocut.html").read_text(encoding="utf-8")
        assert "x&lt;y" in page and "&lt;b&gt;" in page and json.loads((Path(d) / "kirocut.json").read_text(encoding="utf-8"))[0]["score"] == 0.5
    print("report   ok: frontmatter (quotes, lists, blocks), json and escaped html results")
    print("run_evals demo ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["demo"]:
        demo()
    else:
        sys.exit(main(sys.argv[1:]))
