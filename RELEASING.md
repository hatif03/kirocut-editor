# Releasing

Bump `version` in both powers' `plugin.json` files (`plugins/kirocut/plugin.json` and
`plugins/style-match/plugin.json`; they must match). If `.cursor-plugin/plugin.json` or
`.codex-plugin/plugin.json` is present, bump that too. Then check:

```bash
python3 tests/check_plugins.py
```

## Refreshing the lock

`plugins/kirocut/requirements/requirements.lock` pins every Python package, yt-dlp included, so a
TikTok or YouTube change breaks listing until the lock moves. Refresh it on the first Monday of
each month, and whenever the `weekly` workflow opens a "Refresh requirements.lock" issue (the
pinned yt-dlp failed a list that the newest one passed):

```bash
cd plugins/kirocut/requirements
uv pip compile requirements.in --universal --python-version 3.10 --generate-hashes \
  --no-emit-package opencv-python --upgrade -o requirements.lock
cd ../../..
python3 plugins/kirocut/lib/kirocut/lock.py teardown   # style-match's copy of its share
python3 tests/check_plugins.py
PY=~/.kirocut/venv/bin/python python3 tests/run_demos.py        # after setup.py repair installs the new lock
python3 tests/smoke.py
```

`--upgrade` moves every package; `--upgrade-package yt-dlp` moves yt-dlp alone when the rest must
stay. Close the issue with the commit. Users pick up the new pins with `setup.py repair` (doctor
reports the drift). The matte image on Modal takes the same pins from the lock on its next run.

The `weekly` workflow's `python-new` job installs the lock on the newest released Python and runs
every demo. It is allowed to fail; when it does, its summary names the package without wheels, and
the lock's `--python-version` floor or `requirements.in` needs a look before users meet it.

## Version tags

A dependency range on another power resolves against git tags named
`<plugin>--v<version>`. After a release commit is on `main`, from a clean
checkout, tag that version and push the tag. For the versions in the two `plugin.json` files:

```bash
git tag kirocut--v1.0.0 && git push origin kirocut--v1.0.0
git tag style-match--v1.0.0 && git push origin style-match--v1.0.0
```

Tag from a clean checkout, and do not reuse a tag that already exists.

`gsap-skills` and `hyperframes` publish no `<plugin>--v` tags, so kirocut depends on them
without a version range.

## Evals

Each plugin has an `evals/` suite: `<case>/prompt.md` and `<case>/graders/*.md`. `tests/run_evals.py`
runs every case through the Kiro CLI in headless mode (`kiro-cli chat --v3 --no-interactive`) from the
repo root, so the workspace's steering, skills and agents load as they do in the IDE. Every run is a
real model call on your Kiro account: sign in with `kiro-cli login` or set `KIRO_API_KEY`.

```bash
python3 tests/run_evals.py                          # 3 runs per case, both plugins
python3 tests/run_evals.py --runs 1 --case start-asks
python3 tests/run_evals.py demo                     # parses every case and grades canned runs, no model calls
```

Results land in `eval-results/` (`<plugin>.json` and `<plugin>.html`). The script fails when a case
scores under `EVAL_THRESHOLD` (default 0.8). `--runs 1` does one pass instead of three.
`EVAL_MODEL` and `EVAL_JUDGE_MODEL` pin the models, `EVAL_TIMEOUT` the seconds per run (600).

A case's `tools` frontmatter is the only list passed to `--trust-tools` (read, glob, grep and
`@kirocut/kirocut_ask`, plus `use_subagent` where the case fans out). A headless run denies every
other tool, so there is no shell and no file edit. Each case's `dry_run` note goes before its prompt:
write each command and its likely result, treat the editor as installed and named files as present,
and stop at the next question. The suites test the decision path (what the agent routes to, asks
and refuses), not the scripts; those have their own `demo` self-checks and `tests/smoke.py`.

Graders: `skill_used` (the run read that skill's SKILL.md; `skill: any` with `max: 0` for a request
the editor must leave alone), `agent_used` (it started that sub-agent), `regex` on the reply or the
trace, and `llm` (a second headless run with no tools grades the rubric). The asking graders are
`llm` graders that accept kirocut_ask or a question with choices in the reply, since a run without
the workspace MCP config has no kirocut_ask.

### CI

The `evals` job in `.github/workflows/check.yml` installs the Kiro CLI and runs
`python3 tests/run_evals.py --runs 1` on manual dispatch only, and only when the repo has a
`KIRO_API_KEY` secret. Add the secret under Settings > Secrets and variables > Actions to turn it on.
