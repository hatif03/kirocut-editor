"""Read tools: the library, the user's taste. Everything returns data, nothing prints."""
from server import ToolError
from tools import lazy, resolve_edit


def register(s):
    @s.tool("kirocut_library",
            "List the videos and edits in the KiroCut library (name, folder, kind, status, draft, video file), newest first, "
            "or give the library folder. Use it to find an edit before reading or changing it.",
            {"type": "object", "properties": {
                "what": {"type": "string", "enum": ["edits", "path"], "description": "edits (default) or path"},
                "status": {"type": "string", "description": "only edits in this state: cutting, making, ready or done"},
                "limit": {"type": "integer", "description": "at most this many (default 30)"}}},
            read_only=True)
    def kirocut_library(ctx, what="edits", status=None, limit=30):
        lib = lazy("library")
        if what == "path":
            return {"library": str(lib.path(make=False)), "exists": lib.path(make=False).is_dir()}
        rows = lib.entries() if lib.path(make=False).is_dir() else []
        if status:
            rows = [r for r in rows if r.get("status") == status]
        keep = ("name", "dir", "kind", "status", "stage", "round", "draft", "sample", "video", "updated")
        return {"library": str(lib.path(make=False)), "count": len(rows), "edits": [{k: r.get(k) for k in keep} for r in rows[:max(1, int(limit))]]}

    @s.tool("kirocut_taste",
            "Read or change the user's saved editing taste (rules like 'captions bigger'). get returns the settings and the rules; "
            "add saves a correction as a rule for every video, one video or one style; forget removes a rule by id. "
            "To change the video being edited now, use kirocut_scene_ops first, then save the rule here.",
            {"type": "object", "required": ["action"], "properties": {
                "action": {"type": "string", "enum": ["get", "add", "forget"]},
                "section": {"type": "string", "enum": ["Cut", "Captions", "Visuals", "Sound", "Layout"], "description": "add: where the rule belongs"},
                "rule": {"type": "string", "description": "add: the rule in plain words, as the user said it"},
                "setting": {"type": "string", "description": "add: a taste.json key path the scripts read, e.g. captions.size_pct"},
                "value": {"description": "add: the setting's value (any JSON)"},
                "scope": {"type": "string", "description": "add: all (default), or video:<edit name>"},
                "edit": {"type": "string", "description": "the edit the user said it on (add), or the edit to read the video's own rules (get)"},
                "id": {"type": "integer", "description": "forget: the rule id from get"}}})
    def kirocut_taste(ctx, action, section=None, rule=None, setting=None, value=None, scope="all", edit=None, id=None):
        taste = lazy("taste")
        if action == "get":
            folder = str(resolve_edit(edit)) if edit else None
            rules = [{k: r.get(k) for k in ("id", "section", "rule", "setting", "value", "scope", "applied", "off")} for r in taste.load_rules()]
            return {"settings": taste.read_json(), "rules": rules, "text": taste.show(folder) if folder else None}
        if action == "add":
            if not section or not rule:
                raise ToolError("bad_arguments", "add needs section and rule", "section is one of Cut, Captions, Visuals, Sound, Layout")
            if scope.startswith("style:"):
                raise ToolError("bad_arguments", "a style scope needs a style file; use scope all or video:<name>", "")
            try:
                status, r = taste.add(section, rule, setting, value, scope, str(resolve_edit(edit)) if edit else None)
            except SystemExit as e:
                raise ToolError("taste_error", str(e), "")
            return {"status": status, "rule": {k: r.get(k) for k in ("id", "section", "rule", "setting", "value", "scope")}}
        if action == "forget":
            if id is None:
                raise ToolError("bad_arguments", "forget needs the rule id", "call with action get to see ids")
            r = taste.forget(int(id))
            if r is None:
                raise ToolError("no_such_rule", f"no rule {id}", "call with action get to see ids")
            return {"forgot": {"id": r["id"], "rule": r["rule"]}}
        raise ToolError("bad_arguments", f"unknown action {action}", "get, add or forget")
