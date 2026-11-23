# KiroCut view

Shows the KiroCut editor in a panel beside the Kiro chat. It is only needed when the compatibility spike
(`docs/KIRO-COMPAT.md`) says the built-in Simple Browser cannot show the editor. A Kiro Power cannot install an extension,
so this one is installed by hand.

## Build and install

```
cd extensions/kirocut-view
npx @vscode/vsce package --allow-missing-repository
```

That writes `kirocut-view-0.1.0.vsix`. In Kiro: Extensions, the **...** menu, **Install from VSIX**, pick the file.

## Use it

1. Set the embed tier: `py docs/spike/checklist.py record extension_panel=yes`, then `py docs/spike/checklist.py decide`
   (it writes `plugins/kirocut/mcp/compat.json` with `"embed": "extension"`).
2. In the chat say "open the editor". The `kirocut_open_editor` tool returns a link
   `kiro://kirocut.kirocut-view/open?url=...`; clicking it opens the panel. Or run **KiroCut: Open the editor in a panel**
   from the command palette and paste the address.

It frames only `http://127.0.0.1:<port>/` and `http://localhost:<port>/`. The page's cookie is set `SameSite=None; Secure` for a
framed page (`lib/kirocut/authcookie.py`); if the IDE blocks third-party cookies the page cannot sign in and the tool's
browser tier is the way to open it.

## Check it

`python3 tests/check_extension.py` checks the manifest and the JavaScript. Opening it for real is the manual checklist in
`docs/KIRO-COMPAT.md`.
