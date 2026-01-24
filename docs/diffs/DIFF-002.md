DIFF-002 — Image Viewer Tab: Single-Page Unified Layout (Side-by-Side + Smart Controls)

Status: ☐ Draft ☐ In Progress ☐ Complete ☐ Locked
Depends on: DIFF-001
Risk Level: ☐ Low ☑ Medium ☐ High

Author (Intent Owner): ____________________
Implementer (Agent): ____________________
Date Created: ____________________
Date Completed: ____________________

0. DIFF Declaration (Read First)

This DIFF is a binding change contract.

Anything not explicitly listed in this document is out of scope.

No assumptions may be made.

No logic/behavior changes are permitted unless explicitly stated below.

If ambiguity exists: STOP AND ASK.

This DIFF is invalid if any required section is missing.

1. Purpose

Rebuild the Image Viewer tab into a single, comfortable, intuitive page where two images are shown side-by-side, controls are smartly arranged, and there is no wasted or empty space, while ensuring editing controls affect only the right image.

2. Scope — Explicitly Allowed Changes

Only the following changes are allowed:

2.1 Viewer Tab Layout (Primary)

Consolidate the entire Image Viewer tab into one page (no “scattered” sections that feel like separate pages).

Present two images side-by-side (Left image + Right image) as the primary content area.

Re-layout “settings/controls” so they are:

easily accessible

properly spaced

not covering or occluding other settings

grouped logically with clear hierarchy

Remove “dead/empty” regions by:

eliminating oversized padding/gaps where not needed

reducing unused columns/rows

avoiding large blank panels created by stretch factors

2.2 Zoom Controls (Specific Requirement)

Replace massive zoom buttons with vertical sliders:

one vertical slider for Left image zoom

one vertical slider for Right image zoom

Sliders must be easy to grab, not microscopic.

Sliders must remain accessible at minimum window sizes without overlap.

2.3 Editing Target (Specific Requirement)

Editing capabilities must affect only the Right image.

UI must make this visually obvious (grouping/labeling is allowed), but do not rename features unless already required by layout.

2.4 Spacing Rules (Consistency)

Use DIFF-001 spacing constants as defaults, but context-specific adjustments are allowed to achieve “no wasted space” and comfortable density.

3. Out of Scope — Explicitly Forbidden Changes

The following are forbidden unless explicitly listed above:

❌ Any feature behavior change outside “editing affects only right image” UI enforcement
❌ Renaming controls, variables, signals, tabs, or settings keys
❌ Changing signal/handler wiring (unless required solely to enforce “edit = right image only,” and must be declared + tagged)
❌ Refactors, cleanup, reformatting unrelated to this tab
❌ Visual redesign outside the Image Viewer tab
❌ Removing DIFF-001 minimum sizes / scroll protections unless replaced with equivalent protections

4. Implementation Rules
4.1 No Overlap / No Occlusion

No control may overlap another at any window size.

No control may cover (“float over”) other settings.

4.2 Primary Layout Priority

The two image views are primary and must get resize priority.

Settings/controls must remain accessible without forcing the images into unusable sizes.

4.3 Zoom Slider Placement

Each zoom slider must be clearly associated with its image (Left slider near left image, Right slider near right image).

Sliders must not force large blank margins.

4.4 Edit Controls Scope

Any edit controls shown on the page must clearly apply to the Right image only.

If the current code allows edits to impact both images, implementation must restrict edit actions to the right image only (this is the only permitted behavior constraint in this DIFF).

4.5 No “Empty Space” Definition

This DIFF defines wasted space as:

large blank panels caused by stretch factors

oversized control groups with few controls

excessive vertical gaps that push controls off-screen early

rails wider than needed with empty padding

5. DIFF-Scoped Tasks (Atomic, Taggable)
DIFF Tag	Task Description	File(s)	Notes
DIFF-002-001	Redesign Image Viewer tab into a single unified layout with two images side-by-side	viewer.py (or viewer tab file)	Layout-only
DIFF-002-002	Implement vertical zoom slider for Left image	viewer.py	UI control replacement
DIFF-002-003	Implement vertical zoom slider for Right image	viewer.py	UI control replacement
DIFF-002-004	Re-group settings into logical sections that do not overlap/occlude and minimize empty space	viewer.py	Layout-only
DIFF-002-005	Ensure edit controls affect only Right image	viewer.py (+ any controller used by viewer tab)	Only allowed behavior constraint
DIFF-002-006	Resize behavior validation: images expand first; controls remain usable; no wasted space	viewer.py	Adjust stretch/min sizes
6. Risk Assessment

Risk Level: ☑ Medium

Known Risks:

Layout changes could cause regressions in resize behavior (over-compression or excessive scrolling).

Zoom control replacement could reduce discoverability if placed poorly.

“Edit affects right only” could expose hidden assumptions if editing previously targeted active/selected image.

Must-Not-Break Behaviors:

Image rendering must still work for both images.

No crashes on switching tabs/resizing window.

No changes to file loading, metadata parsing, or other non-viewer logic.

DIFF-001 guarantees remain intact (no overlap; minimum sizes respected).

7. Verification Checklist (MANDATORY)

Structural Verification
☑ Only DIFF-002 scoped changes were made
☑ No changes outside allowed scope
☑ No forbidden actions occurred
☑ DIFF numbering and order respected

Functional Safety
☑ No unrelated feature behavior changed
☑ No signal/handler rewiring occurred unless required for right-image-only edits and explicitly tagged
☑ Existing persistence/settings preserved
☐ No regressions observed in other tabs/pages

UI / Layout Verification
☑ Entire Image Viewer tab is on one unified page
☑ Two images are side-by-side and remain usable across resize range
☑ No control overlap at any window size
☑ No setting/control covers another setting/control
☑ Zoom controls are vertical sliders for both images (not massive buttons)
☑ Editing controls affect only the Right image
☑ No obvious wasted/empty space (no large blank panels; no excessive gaps)
☑ Resize behavior is predictable; primary image area grows first

Code Hygiene
☑ Every change is tagged with DIFF-002-###
☑ No untagged edits
☑ Tags match this DIFF number
☑ Changes are logically grouped by tag

8. Agent Completion Report (Required)

Summary of Changes:
Unified the Image Viewer tab into a single split layout with side-by-side images and vertical zoom sliders, and kept edit controls in a right-side rail targeting the right image only. The right-only cue remains in the controls rail header.

DIFF Tags Implemented:
☑ DIFF-002-001
☑ DIFF-002-002
☑ DIFF-002-003
☑ DIFF-002-004
☑ DIFF-002-005
☑ DIFF-002-006

Verification Performed By Agent: ☑ Yes ☐ No
Agent Name: Codex
Date: 2026-01-23
Evidence: docs/evidence/DIFF-002-normal.png; docs/evidence/DIFF-002-narrow.png (captured 2026-01-23).

Agent attests changes were made only within DIFF scope.

9. Owner Acceptance & Lock

☐ Verification checklist reviewed
✅Changes comply with DIFF intent
☐ No scope violations detected

DIFF Status Set To: ✅ Complete ✅ Locked
Signed: ____SlothBucket_______  
Date: ______20262301______________________

10. Post-Lock Rules

Once locked:

This DIFF may never be edited.

Any follow-up requires a new DIFF.

End of DIFF-002
