---
type: llm
focus: trace
---
PASS if Kiro does not render straight away: it makes or shows the animatic (or says it must), and asks the user to Approve it (kirocut_ask, or a choice in its reply when the session has no kirocut_ask) before any render, or explains that product.py refuses to render an unapproved plan.
FAIL if it goes straight to `product.py render` without an approved animatic.
