# Requirements

## Introduction

KiroCut is the video editor inside this Kiro workspace. The person opens the folder, says "edit my video", and approves each stage. The window is local. Kiro runs the skills.

## Requirements

### Requirement 1: Open the editor from Kiro

**User Story:** As someone working in Kiro, I want this folder to be the editor, so that I do not install a separate app to cut a video.

#### Acceptance Criteria

1. WHEN the workspace opens, the system SHALL load `.kiro/steering/` and `AGENTS.md`.
2. WHEN the person says "edit my video", the system SHALL follow `plugins/kirocut/skills/start/SKILL.md`.
3. WHEN a required tool is missing, the system SHALL run the setup skill before cutting.

### Requirement 2: Cut the take

**User Story:** As a speaker, I want retakes, false starts and long pauses removed, so that the video starts from a clean take.

#### Acceptance Criteria

1. WHEN a video file is given, the system SHALL transcribe it and propose cuts.
2. WHEN the person accepts or edits those cuts, the system SHALL preview the result before a styled render.
3. IF the person leaves a note on the review page, THEN the system SHALL apply that note on the next round.

### Requirement 3: Render the edit

**User Story:** As a person finishing a video, I want captions, zooms and cards on my approved cut, so that I can export one file.

#### Acceptance Criteria

1. WHEN the cut is approved, the system SHALL render with the style selected for that video.
2. WHEN a render finishes, the system SHALL open it on the review page.
3. WHILE a render is running, the system SHALL show which step it is on.

### Requirement 4: Brand

**User Story:** As a person opening the window, I want to see KiroCut, so that I know this is the editor inside Kiro.

#### Acceptance Criteria

1. The home page and the review page SHALL show the name KiroCut and the K mark.
2. The welcome line SHALL say that KiroCut turns the Kiro IDE into a video editor.
3. The repo SHALL NOT ship example links to other creators' accounts.
