---
type: llm
focus: trace
---
PASS if, before planning or recording any video, Kiro asks the brief: what the video must show, who will watch, and the one action at the end (any two of these count), through kirocut_ask, or as choices in its reply when the session has no kirocut_ask (headless eval runs).
FAIL if it plans, records or renders a video without asking what it must show.
