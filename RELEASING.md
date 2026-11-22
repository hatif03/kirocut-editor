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
PY=~/.kirocut/venv/bin/python tests/demos.sh        # after setup.py repair installs the new lock
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

Each plugin has an `evals/` suite. Every run is a
real model call on your account. Run both suites from the repo root:

```bash
tests/run_evals.sh                       # 3 runs per case, both plugins
tests/run_evals.sh --runs 1 --case start-asks
```

Results land in `eval-results/` (`<plugin>.json` and `<plugin>.html`). The script fails when a case
scores under `EVAL_THRESHOLD` (default 0.8) and stops at `EVAL_MAX_COST` dollars per suite
(default 15). `--runs 1` does one pass instead of three.

Why the repo root: kirocut depends on style-match, and the eval runner does not install
dependencies or take `--plugin-dir`. Each kirocut case lists both plugin folders in its
`plugins:` frontmatter, and eval only loads plugin folders under the directory it was pointed at,
so it has to point at the root (`--eval-dir plugins/kirocut/evals`). Running from
`plugins/kirocut` fails with "outside the containment root".

Headless eval runs have no AskUserQuestion tool (it is listed in `allowed_tools` but never
offered), so the asking graders are `llm` graders that accept a question with choices in the reply.

Eval runs also have no shell: granting Bash needs the OS sandbox, which refuses to start on a Mac
whose `~/.docker` holds a symlink, and the editor is never installed in the run's temporary home.
So each case sets `append_system_prompt` to a dry run: write each command and its likely result,
treat the editor as installed and named files as present, and stop at the next question. The
suites test the decision path (what the agent routes to, asks and refuses), not the scripts;
those have their own `demo` self-checks and `tests/smoke.py`. The judge is Sonnet
(`EVAL_JUDGE` to change it): Haiku failed replies that met the rubric.

### CI

The `evals` job in `.github/workflows/check.yml` runs `tests/run_evals.sh --runs 1` on manual
dispatch only, and only when the repo has an `ANTHROPIC_API_KEY` secret. Add the secret under
Settings > Secrets and variables > Actions to turn it on.
