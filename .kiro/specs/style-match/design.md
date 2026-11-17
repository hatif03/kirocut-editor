# Design

## Overview

Style match is the existing style-match skill, branded inside KiroCut. It measures reference videos. It does not browse a directory of other creators.

```
person pastes links or a profile
        ↓
style-match  →  style-matches/<id>/  (style.json and the write-up)
        ↓
home page style list  (tab: Matched styles)
        ↓
style-edit renders the person's cut with that style.json
```

## Components

- `plugins/style-match/skills/style-match/` downloads and measures the references the person named.
- `plugins/kirocut/lib/kirocut/links.py` classifies a link as a video or a profile. Tests use fake handles only.
- The home page (`home.html`) labels the action "Match a style" and the shelf "Matched styles".
- `style.json` is what style-edit reads. A later correction can land in `style.overrides.json` or in taste.

## What not to add

No fixture profiles, no README embeds, and no onboarding copy that points at a real creator's account. A link appears only when the person pastes it.
