# Requirements

## Introduction

Style match is a KiroCut feature. The person supplies the references. KiroCut measures how those videos are edited and applies that measurement to their own footage. The repo does not include other people's accounts as examples.

## Requirements

### Requirement 1: Take references from the person

**User Story:** As someone with a look in mind, I want to paste a few videos edited the same way, so that my edit can follow that format.

#### Acceptance Criteria

1. WHEN the person pastes 3 to 6 video links, the system SHALL treat them as one style.
2. WHEN the person pastes a profile, the system SHALL let them tick which videos to measure.
3. IF fewer references are given, THEN the system SHALL still save a style and say what it measured.
4. The product SHALL NOT ship sample links to other creators' Instagram, TikTok, or YouTube accounts.

### Requirement 2: Measure the edit, not the person

**User Story:** As someone matching a format, I want numbers for the cut, zooms, captions, cards and sound, so that the style is a setting I can rename and reuse.

#### Acceptance Criteria

1. WHEN a style is saved, the system SHALL record pace, cuts, zooms, caption treatment, cards and sound.
2. WHEN the person renames the style, the system SHALL keep the measurements.
3. The window SHALL call this action "Match a style".

### Requirement 3: Apply it to their footage

**User Story:** As someone with my own take, I want that style on my video, so that the format and my footage stay separate.

#### Acceptance Criteria

1. WHEN a video is made with a matched style, the system SHALL cut the person's footage first, then render in that style.
2. WHEN the person corrects the result, the system SHALL be able to save the correction as a rule on that style.
3. A matched style SHALL appear under Matched styles, separate from styles they built by hand.
