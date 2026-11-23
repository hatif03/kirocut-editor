"""Questions for the user, in the IDE.

Skills ask here, not in the editor window (askhook.py's question cards are the older route). A question
goes one of two ways, decided per call:

  form   the client supports MCP elicitation (it advertised it at initialize, and compat.json does not say "chat"): the IDE
         shows its own form and the answers come back in the same tool call
  chat   it does not: kirocut_ask returns the question as numbered text; the agent asks it in the chat, and kirocut_answer
         turns the user's reply ("1", "2 and 3", "the second one, but shorter") into the same structured answers

Both give answers as {question id: option label}, or a list of labels for a multi-select question. A free-typed answer
comes back as {"other": "text"} when the question allows it.
"""
import json
import re
import time
import uuid
from pathlib import Path

from server import ToolError
from tools_editor import compat

ASKS = {}   # ask_id -> the questions, for kirocut_answer
STARTED = {}   # ask_id -> (edit folder or None, when it was asked)
MAX_Q, MAX_OPT = 6, 8


def edit_folder(edit):
    """The edit a question is about, or None (a question before any edit exists, or a name that is not one)."""
    if not edit:
        return None
    try:
        from tools import resolve_edit
        return resolve_edit(edit)
    except ToolError:
        return None


def note_wait(folder, start, end):
    """The time the user took to answer, on the edit's review/asks.jsonl: review.py timings leaves it out of "Made in"."""
    if folder is None or start is None:
        return
    try:
        (folder / "review").mkdir(parents=True, exist_ok=True)
        with open(folder / "review" / "asks.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"start": round(start, 2), "end": round(end, 2)}) + "\n")
    except OSError:
        pass

QUESTIONS = {"type": "array", "minItems": 1, "maxItems": MAX_Q, "items": {
    "type": "object", "required": ["id", "text", "options"], "properties": {
        "id": {"type": "string", "description": "A short key for the answer, e.g. platform"},
        "text": {"type": "string", "description": "The question, one sentence"},
        "options": {"type": "array", "minItems": 2, "maxItems": MAX_OPT, "items": {"type": "object", "required": ["label"], "properties": {
            "label": {"type": "string"}, "description": {"type": "string"}}},
            "description": "2 to 8 choices; put the recommended one first and end its label with (Recommended)"},
        "multi": {"type": "boolean", "description": "More than one choice allowed"},
        "allow_other": {"type": "boolean", "description": "The user may type their own answer"}}}}


def clean(questions):
    if not isinstance(questions, list) or not 1 <= len(questions) <= MAX_Q:
        raise ToolError("bad_arguments", f"ask 1 to {MAX_Q} questions at a time", "split a long intake into rounds")
    out, seen = [], set()
    for q in questions:
        qid, text, opts = str(q.get("id") or "").strip(), str(q.get("text") or "").strip(), q.get("options") or []
        labels = [str(o.get("label") if isinstance(o, dict) else o).strip() for o in opts]
        if not qid or not text or len(labels) < 2 or len(set(labels)) != len(labels) or qid in seen or len(labels) > MAX_OPT:
            raise ToolError("bad_arguments", f"question {qid or text[:20]!r} needs a unique id, text and 2 to {MAX_OPT} different options", "")
        seen.add(qid)
        desc = [str(o.get("description") or "") if isinstance(o, dict) else "" for o in opts]
        out.append({"id": qid, "text": text, "labels": labels, "desc": desc, "multi": bool(q.get("multi")), "other": bool(q.get("allow_other"))})
    return out


# ---- chat mode
def render_text(qs):
    """The questions as numbered text for the agent to say as it is."""
    lines = []
    for i, q in enumerate(qs, 1):
        lines.append(f"{i}. {q['text']}" + ("  (pick any)" if q["multi"] else "  (pick one)"))
        for n, (lab, d) in enumerate(zip(q["labels"], q["desc"]), 1):
            lines.append(f"   {n}) {lab}" + (f": {d}" if d else ""))
        if q["other"]:
            lines.append(f"   {len(q['labels']) + 1}) Something else (type it)")
    lines.append("Reply with the number" + (" for each question, one per line like '1. 2'" if len(qs) > 1 else "") + ".")
    return "\n".join(lines)


def _pick(q, text):
    """The labels one reply fragment picks for question q: numbers, 'all', 'none', or a label (or its start) typed out."""
    t = text.strip().strip(".").lower()
    if not t:
        return [], None
    if t in ("none", "skip", "no", "nothing"):
        return [], None
    if t == "all" and q["multi"]:
        return list(q["labels"]), None
    got = []
    ords = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "last": len(q["labels"])}
    t = re.sub(r"\b(" + "|".join(ords) + r")\b", lambda m: str(ords[m.group(1)]), t)
    for m in re.finditer(r"\d+", t):
        n = int(m.group())
        if 1 <= n <= len(q["labels"]) and q["labels"][n - 1] not in got:
            got.append(q["labels"][n - 1])
    if got:
        return (got if q["multi"] else got[:1]), None
    low = {lab.lower().replace("(recommended)", "").strip(): lab for lab in q["labels"]}
    for key, lab in low.items():
        if t == key or key.startswith(t) and len(t) >= 3 or t.startswith(key):
            got.append(lab)
    if got:
        return (got if q["multi"] else got[:1]), None
    return [], (text.strip() if q["other"] else None)


def parse_reply(qs, reply):
    """{question id: label | [labels] | {"other": text} | None}. A reply for several questions has one per line ('1. 2',
    '2: 1, 3'); for one question the whole reply is its answer."""
    reply = (reply or "").strip()
    parts = {}
    if len(qs) == 1:
        parts[1] = reply
    else:
        order = 0
        for ln in reply.splitlines():
            m = re.match(r"^\s*(\d+)\s*[.:)\-]\s*(.*)$", ln)
            if m:
                parts[int(m.group(1))] = m.group(2)
            elif ln.strip():
                order += 1
                parts.setdefault(order, ln)
    out = {}
    for i, q in enumerate(qs, 1):
        picked, other = _pick(q, parts.get(i, ""))
        if other is not None:
            out[q["id"]] = {"other": other}
        elif q["multi"]:
            out[q["id"]] = picked
        else:
            out[q["id"]] = picked[0] if picked else None
    return out


# ---- form mode
def form_schema(qs):
    """A flat MCP elicitation schema: an enum string per single choice, a boolean per option of a multi choice, an optional
    string for an 'other' answer (elicitation schemas hold primitives only)."""
    props, req = {}, []
    for q in qs:
        if q["multi"]:
            for n, lab in enumerate(q["labels"]):
                props[f"{q['id']}__{n}"] = {"type": "boolean", "title": lab, "description": q["text"] if n == 0 else lab, "default": False}
        else:
            props[q["id"]] = {"type": "string", "title": q["text"], "enum": q["labels"],
                              "description": "; ".join(f"{l}: {d}" for l, d in zip(q["labels"], q["desc"]) if d) or q["text"]}
            req.append(q["id"])
        if q["other"]:
            props[f"{q['id']}__other"] = {"type": "string", "title": f"{q['text']} (or type your own)"}
    return {"type": "object", "properties": props, **({"required": req} if req else {})}


def from_form(qs, content):
    out = {}
    for q in qs:
        other = str(content.get(f"{q['id']}__other") or "").strip()
        if q["multi"]:
            out[q["id"]] = [lab for n, lab in enumerate(q["labels"]) if content.get(f"{q['id']}__{n}") is True]
        else:
            out[q["id"]] = content.get(q["id"]) if content.get(q["id"]) in q["labels"] else None
        if other and not out[q["id"]]:
            out[q["id"]] = {"other": other}
    return out


def register(s):
    @s.tool("kirocut_ask",
            "Ask the user one to six multiple-choice questions. If the IDE can show a form it does, and the answers come back here "
            "(mode form). If it cannot, you get the questions as numbered text (mode chat): say that text to the user as it is, wait for their "
            "reply, then call kirocut_answer with the ask_id and their reply. Put the recommended option first. Never ask for an API key here.",
            {"type": "object", "required": ["questions"], "properties": {
                "questions": QUESTIONS, "intro": {"type": "string", "description": "One line before the questions (optional)"},
                "edit": {"type": "string", "description": "The edit the questions are about, when there is one: the time the user "
                                                         "takes to answer is left out of its 'Made in' time"}}})
    def kirocut_ask(ctx, questions, intro=None, edit=None):
        qs = clean(questions)
        folder = edit_folder(edit)
        t0 = time.time()
        mode = compat().get("elicitation", "auto")
        if mode != "chat" and ctx.can_elicit:
            got = ctx.elicit((intro + "\n" if intro else "") + (qs[0]["text"] if len(qs) == 1 else "A few questions"), form_schema(qs))
            if got is not None:
                note_wait(folder, t0, time.time())
                if got.get("action") == "accept":
                    return {"mode": "form", "answered": True, "answers": from_form(qs, got.get("content") or {})}
                return {"mode": "form", "answered": False, "action": got.get("action", "cancel"),
                        "next": "The user dismissed the form. Ask in chat only if you cannot go on without it."}
        aid = uuid.uuid4().hex[:8]
        ASKS[aid] = qs
        STARTED[aid] = (folder, t0)
        return {"mode": "chat", "answered": False, "ask_id": aid, "say_to_user": (intro + "\n\n" if intro else "") + render_text(qs),
                "next": "Say say_to_user in your reply, stop, and when the user answers call kirocut_answer with this ask_id and their words."}

    @s.tool("kirocut_answer",
            "Turn the user's chat reply to a kirocut_ask (mode chat) into structured answers. Pass the ask_id and the user's words as they wrote them.",
            {"type": "object", "required": ["ask_id", "reply"], "properties": {
                "ask_id": {"type": "string"}, "reply": {"type": "string", "description": "The user's reply, unedited"}}}, read_only=True)
    def kirocut_answer(ctx, ask_id, reply):
        qs = ASKS.get(ask_id)
        if not qs:
            raise ToolError("no_such_ask", f"no open question {ask_id}", "ask again with kirocut_ask")
        answers = parse_reply(qs, reply)
        missing = [q["id"] for q in qs if answers[q["id"]] in (None, []) and not q["multi"]]
        if not missing:
            ASKS.pop(ask_id, None)
            folder, t0 = STARTED.pop(ask_id, (None, None))
            note_wait(folder, t0, time.time())
        return {"answers": answers, "unanswered": missing,
                "next": ("Ask again only for: " + ", ".join(missing)) if missing else "Carry on with these answers."}
