// KiroCut spike probe. Plain JavaScript, no build step, no dependencies.
// Commands: "KiroCut probe: open a local page in a panel" asks for a URL (the spike_page tool prints one)
// and frames it in a webview. A URI handler does the same for  <scheme>://kirocut.kirocut-probe/open?url=...
const vscode = require("vscode");

function panel(url) {
  const p = vscode.window.createWebviewPanel("kirocutProbe", "KiroCut probe", vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true });
  const origin = new URL(url).origin;
  p.webview.html = `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; frame-src ${origin}; style-src 'unsafe-inline';">
<style>html,body,iframe{margin:0;padding:0;width:100%;height:100%;border:0}</style></head>
<body><iframe src="${url}"></iframe></body></html>`;
  return p;
}

function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand("kirocutProbe.open", async (arg) => {
    const url = typeof arg === "string" ? arg : await vscode.window.showInputBox({ prompt: "URL of the local page", value: "http://127.0.0.1:" });
    if (url) panel(url);
  }));
  context.subscriptions.push(vscode.window.registerUriHandler({
    handleUri(uri) {
      const url = new URLSearchParams(uri.query).get("url");
      if (url && url.startsWith("http://127.0.0.1:")) panel(url);
    },
  }));
}
function deactivate() {}
module.exports = { activate, deactivate };
