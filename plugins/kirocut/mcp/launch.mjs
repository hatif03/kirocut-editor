#!/usr/bin/env node
// Starts KiroCut's MCP server with the right Python on any computer, so one mcp.json works on Windows and Mac.
//   node launch.mjs            the server on stdio (stdin and stdout pass straight through)
//   node launch.mjs --which    print the Python it would use and exit
//   node launch.mjs --run <script.py> [args]   run a script (a hook) with that Python instead of the server
// Order: the editor's venv ($KIROCUT_HOME/venv, made by the setup skill), then `py -3` on Windows, then python3, then python.
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const win = process.platform === "win32";
const home = (process.env.KIROCUT_HOME || "").trim() || join(homedir(), ".kirocut");
const venv = join(home, "venv", win ? "Scripts/python.exe" : "bin/python");

function works(cmd, pre = []) {
  const r = spawnSync(cmd, [...pre, "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"], { stdio: "ignore" });
  return r.status === 0;
}

function python() {
  if (existsSync(venv) && works(venv)) return [venv, []];
  const tries = win ? [["py", ["-3"]], ["python", []], ["python3", []]] : [["python3", []], ["python", []]];
  for (const [cmd, pre] of tries) if (works(cmd, pre)) return [cmd, pre];
  return null;
}

const py = python();
if (!py) {
  process.stderr.write("KiroCut needs Python 3.9 or newer. " +
    (win ? "Install it with: winget install -e --id Python.Python.3.12\n" : "Install it with: brew install python\n"));
  process.exit(1);
}
if (process.argv.includes("--which")) {
  console.log([py[0], ...py[1]].join(" "));
  process.exit(0);
}
// node launch.mjs --run <script.py> [args]   run any KiroCut script with that Python (the hooks use it), stdin passes through
const at = process.argv.indexOf("--run");
const target = at >= 0 ? [resolve(process.argv[at + 1]), ...process.argv.slice(at + 2)] : [join(here, "server.py")];
const child = spawn(py[0], [...py[1], ...target], { stdio: "inherit", env: { ...process.env, PYTHONUTF8: "1" } });
child.on("exit", (code, signal) => process.exit(signal ? 1 : code ?? 0));
for (const s of ["SIGINT", "SIGTERM"]) process.on(s, () => child.kill(s));
