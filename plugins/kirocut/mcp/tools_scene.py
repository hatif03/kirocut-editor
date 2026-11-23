"""Scene tools: read the scene, change it with ops, add items, undo the agent's changes.

An edit's scene (scene.json) is the one place a change is made. When the review page for the edit is open, a change
goes through its server (one undo step there, the page redraws on its next poll). Otherwise it is written to
scene.json directly. Either way it is logged in review/agent.json with the ops that undo it.
"""
import json
import urllib.error
import urllib.request

from server import ToolError
from tools import lazy, resolve_edit

EDIT = {"type": "string", "description": "The edit: its folder, or its name in the library"}
ALT = {"type": "string", "description": "A version of the edit (a trial reel, 't1'). Omit for the main scene."}


def scene_mod():
    return lazy("scene")


def wrap(fn):
    """SceneError (and a bad file) as a ToolError the agent can act on."""
    def run(*a, **k):
        sc = scene_mod()
        try:
            return fn(*a, **k)
        except sc.SceneError as e:
            raise ToolError("scene_error", str(e), "kirocut_scene_show --at <t> names the items and their ids; ops are listed in SCENE.md")
        except (OSError, ValueError) as e:
            raise ToolError("scene_unreadable", f"{type(e).__name__}: {e}", "the edit may not be a scene yet: open it in the editor first")
    run.__name__ = fn.__name__
    return run


def changed_rows(sc, ids):
    return [r for t in scene_mod().show_data(sc, limit=10 ** 6)["tracks"] for r in t["items"] if r["id"] in ids]


def apply_change(folder, ops, why, alt=None):
    """(scene, change, through_page): the ops applied as the agent's one change."""
    sc = scene_mod()
    if not isinstance(ops, list) or not ops:
        raise ToolError("bad_arguments", "ops must be a non-empty list", "e.g. [{\"op\":\"trim\",\"item\":\"v1\",\"edge\":\"start\",\"by\":2}]")
    page = bool(sc.server(folder))
    after, change = sc.agent_ops(folder, ops, why, alt)
    return after, change, page


def result(folder, after, change, page, ops):
    ids = list(dict.fromkeys(i for i in (change or {}).get("items") or []))
    return {"change": ({k: change.get(k) for k in ("n", "why", "t", "items")} if change else None), "nothing_changed": change is None,
            "duration": round(after["duration"], 3), "items": changed_rows(after, set(ids)),
            "through_page": page, "undo_with": {"tool": "kirocut_scene_undo", "n": change["n"]} if change else None}


def register(s):
    @s.tool("kirocut_scene_show",
            "Read an edit's scene as JSON: tracks and items (id, type, start, end, text or file, box), the AI's cuts, the spoken words "
            "with times, and the pauses between them. Pass at (seconds) to see only what is on screen then and the words around it. "
            "Always read this before changing a scene so you use real item ids and times.",
            {"type": "object", "required": ["edit"], "properties": {
                "edit": EDIT, "at": {"type": "number", "description": "Scene seconds: only items on screen then, words within 3 s"},
                "alt": ALT, "limit": {"type": "integer", "description": "Items per track before the middle is left out (default 80)"}}},
            read_only=True)
    @wrap
    def kirocut_scene_show(ctx, edit, at=None, alt=None, limit=80):
        sc = scene_mod()
        folder = resolve_edit(edit)
        return sc.show_data(sc.scene_of(folder, alt), None if at is None else float(at), sc.name_of(alt), int(limit))

    @s.tool("kirocut_scene_ops",
            "Change an edit's scene with ops, applied in order as one undoable change the user sees on the editor page. Ops: "
            "set {item, props}, add {track, item, index?}, remove {item}, move {item, track, index?}, trim {item, edge: start|end, by: seconds}, "
            "split {item, t}, cut {start, end} (take those scene seconds out of the footage and close the gap), track {track, props}, "
            "add_track {track, index?}, remove_track {track}, asset {id, asset}. Item ids and "
            "times come from kirocut_scene_show. On the main footage track a trim closes or opens the gap (the magnet). "
            "Say why in one short line: the page shows it. Fields are in plugins/kirocut/lib/kirocut/SCENE.md.",
            {"type": "object", "required": ["edit", "ops", "why"], "properties": {
                "edit": EDIT, "ops": {"type": "array", "items": {"type": "object"}, "description": "The ops, in order"},
                "why": {"type": "string", "description": "One line the page shows next to the change"}, "alt": ALT}})
    @wrap
    def kirocut_scene_ops(ctx, edit, ops, why, alt=None):
        folder = resolve_edit(edit)
        after, change, page = apply_change(folder, ops, why, alt)
        return result(folder, after, change, page, ops)

    @s.tool("kirocut_scene_add",
            "Put one new item on the scene: text (text), image, video or audio (src: a file), or a shape. It goes on a free track of its kind, "
            "never over the footage. x and y are the item's centre in canvas pixels, w and h its size; props sets any other field "
            "(box, color, size, anim, keys...). Use for 'add Link in bio at 0:20' or 'put the logo top right'.",
            {"type": "object", "required": ["edit", "type", "start", "why"], "properties": {
                "edit": EDIT, "type": {"type": "string", "enum": ["text", "image", "video", "audio", "shape"]},
                "start": {"type": "number", "description": "Scene seconds"}, "end": {"type": "number", "description": "Scene seconds (default start + 3, or the file's length)"},
                "text": {"type": "string"}, "src": {"type": "string", "description": "A file path (copied into the edit's media folder)"},
                "track": {"type": "string", "description": "A track id or name to prefer"},
                "x": {"type": "number"}, "y": {"type": "number"}, "w": {"type": "number"}, "h": {"type": "number"},
                "props": {"type": "object", "description": "Other item fields"}, "why": {"type": "string"}, "alt": ALT}})
    @wrap
    def kirocut_scene_add(ctx, edit, type, start, why, end=None, text=None, src=None, track=None, x=None, y=None, w=None, h=None,
                          props=None, alt=None):
        sc = scene_mod()
        folder = resolve_edit(edit)
        scene = sc.scene_of(folder, alt)
        before = {i["id"] for t in scene["tracks"] for i in t["items"]}
        geo = {"x": x, "y": y, "w": w, "h": h}
        ops = sc.add_op(folder, scene, type, float(start), None if end is None else float(end), src, text, track, geo, props or {})
        after, change, page = apply_change(folder, ops, why, alt)
        out = result(folder, after, change, page, ops)
        out["added"] = [i["id"] for t in after["tracks"] for i in t["items"] if i["id"] not in before]
        return out

    @s.tool("kirocut_scene_cards",
            "Put the cards from the edit's plan.json (made by the overlays skill or the card filler) on the scene as items, either every new one "
            "or the one on screen at each time in at.",
            {"type": "object", "required": ["edit", "why"], "properties": {
                "edit": EDIT, "at": {"type": "array", "items": {"type": "number"}}, "why": {"type": "string"}, "alt": ALT}})
    @wrap
    def kirocut_scene_cards(ctx, edit, why, at=None, alt=None):
        sc = scene_mod()
        folder = resolve_edit(edit)
        plan_f = folder / "plan.json"
        if not plan_f.is_file():
            raise ToolError("no_plan", f"{folder.name} has no plan.json", "cards come from the overlays skill")
        ops = sc.cards_ops(folder, sc.scene_of(folder, alt), sc.jload(plan_f), [float(t) for t in at or []])
        if not ops:
            return {"nothing_changed": True, "change": None, "items": [], "note": "no new cards"}
        after, change, page = apply_change(folder, ops, why, alt)
        return result(folder, after, change, page, ops)

    @s.tool("kirocut_scene_changes",
            "List the changes the agent made to an edit's scene, each with its number, why, time and whether it is undone.",
            {"type": "object", "required": ["edit"], "properties": {"edit": EDIT, "alt": ALT}}, read_only=True)
    @wrap
    def kirocut_scene_changes(ctx, edit, alt=None):
        sc = scene_mod()
        folder = resolve_edit(edit)
        _, log = sc.read_changes(folder, alt)
        return {"changes": [{k: c.get(k) for k in ("n", "why", "t", "items", "undone", "when")} for c in log]}

    @s.tool("kirocut_scene_undo",
            "Undo (or redo) one of the agent's earlier scene changes by its number from kirocut_scene_changes. The user's own edits made "
            "since stay. Use when the user says 'undo that' or 'put it back'.",
            {"type": "object", "required": ["edit"], "properties": {
                "edit": EDIT, "n": {"type": "integer", "description": "Default: the newest change not undone (redo: the newest undone)"},
                "redo": {"type": "boolean", "description": "Redo a change that was undone"}, "alt": ALT}})
    @wrap
    def kirocut_scene_undo(ctx, edit, n=None, redo=False, alt=None):
        sc = scene_mod()
        folder = resolve_edit(edit)
        if n is None:   # "undo that": the newest change still in effect
            _, log = sc.read_changes(folder, alt)
            last = [c for c in log if bool(c.get("undone")) == bool(redo)]
            if not last:
                raise ToolError("nothing_to_undo", "no change of the agent's to " + ("redo" if redo else "undo"), "kirocut_scene_changes lists them")
            n = last[-1]["n"]
        url = sc.server(folder)
        if url:   # the page's server journals it and redraws
            base, tok = url.split("/?t=", 1)
            req = urllib.request.Request(f"{base}/scene/agent?t={tok}", json.dumps({"n": int(n), "undo": not redo, "alt": alt}).encode(),
                                         {"Content-Type": "application/json"}, method="POST")
            try:
                urllib.request.urlopen(req, timeout=60).read()
            except urllib.error.HTTPError as e:
                raise ToolError("scene_error", json.loads(e.read() or b"{}").get("error") or f"the page answered {e.code}", "")
            after = sc.load(folder, sc.name_of(alt))
        else:
            after = sc.undo_change(folder, int(n), not redo, alt)
        return {"n": int(n), "state": "redone" if redo else "undone", "duration": round(after["duration"], 3), "through_page": bool(url)}
