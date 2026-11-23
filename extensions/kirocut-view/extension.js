// KiroCut view: the editor page, in a panel beside the chat. Plain JavaScript, no build step, no dependencies.
//
// The page is served by KiroCut's own local server (home.py or review.py) on 127.0.0.1 and carries its token in the
// address. This extension only frames it. It opens an address when:
//   - the chat shows a link  kiro://kirocut.kirocut-view/open?url=<address>  (the kirocut_open_editor tool makes it), or
//   - the command "KiroCut: Open the editor in a panel" is run (it asks for the address, or takes it as an argument).
// Only http://127.0.0.1:<port>/ and http://localhost:<port>/ are framed. Anything else is refused.
const vscode = require("vscode");

const LOCAL = /^http:\/\/(127\.0\.0\.1|localhost):\d{2,5}\//;
let panel = null;

/** The address to frame, or null when it is not a page this computer serves. */
function localUrl(text) {
  try {
    const u = new URL(String(text));
    return LOCAL.test(u.href) ? u.href : null;
  } catch (e) {
    return null;
  }
}

function html(url) {
  const origin = new URL(url).origin;
  return `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; frame-src ${origin}; style-src 'unsafe-inline';">
<style>html,body,iframe{margin:0;padding:0;width:100%;height:100%;border:0;background:#111}</style></head>
<body><iframe src="${url.replace(/"/g, "&quot;")}" allow="clipboard-read; clipboard-write; autoplay"></iframe></body></html>`;
}

function show(url) {
  const ok = localUrl(url);
  if (!ok) {
    vscode.window.showWarningMessage("KiroCut only shows pages served on this computer.");
    return;
  }
  if (panel) {
    panel.webview.html = html(ok);
    panel.reveal(vscode.ViewColumn.Beside, true);
    return;
  }
  panel = vscode.window.createWebviewPanel("kirocutView", "KiroCut", { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true },
    { enableScripts: true, retainContextWhenHidden: true });
  panel.webview.html = html(ok);
  panel.onDidDispose(() => { panel = null; });
}

function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand("kirocut.openEditor", async (arg) => {
    const url = typeof arg === "string" ? arg : await vscode.window.showInputBox({
      prompt: "Address of the KiroCut editor (the kirocut_open_editor tool prints it)", value: "http://127.0.0.1:" });
    if (url) show(url);
  }));
  context.subscriptions.push(vscode.window.registerUriHandler({
    handleUri(uri) {
      if (uri.path !== "/open") return;
      const url = new URLSearchParams(uri.query).get("url");
      if (url) show(url);
    },
  }));
}

function deactivate() {}

module.exports = { activate, deactivate, localUrl, html };
