DIFF-003 — Implement Full Image Edit Pipeline with Non-Destructive Workflow

Status: ☐ Draft ☐ In Progress ☐ Complete ☐ Locked
Depends on: None
Risk Level: ☐ Low ☐ Medium ☑ High

Author (Intent Owner): ____________________
Implementer (Agent): ____________________
Date Created: ____________________
Date Completed: ____________________

0. DIFF Declaration (Read First)

This DIFF is a binding change contract.

Anything not explicitly listed in this document is out of scope

No assumptions may be made

No logic, behavior, or feature changes are permitted unless explicitly stated

If ambiguity exists, STOP AND ASK

This DIFF is invalid if any required section is missing.

1. Purpose (Why this DIFF exists)

Make every existing image edit control in the Full Image Viewer tab functional with standard photo editor behavior, delivered through a non-destructive workflow and safe save behavior that preserves originals unless explicitly overwritten, while keeping UI changes minimal and the app responsive.

2. Scope — Explicitly Allowed Changes

List only what may be changed.

Rules:

Use bullet points

Be concrete

If it’s not here, it’s forbidden

Allowed:

☐ Implement functional behavior for Basic tone controls: Exposure, Brightness, Contrast, Gamma, Black Point, White Point

☐ Implement functional behavior for Highlights & shadows controls: Highlights, Shadows, Whites, Blacks

☐ Implement functional behavior for Color / white balance controls: Temperature (Kelvin / Warmth), Tint (Green-Magenta), Saturation, Vibrance, Hue

☐ Implement functional behavior for Detail / sharpness controls: Sharpening, Sharpen Radius, Sharpen Amount, Sharpen Threshold, Detail, Edge Masking

☐ Implement functional behavior for Texture / micro-contrast controls: Clarity, Texture, Structure, Midtone Contrast, Local Contrast

☐ Implement functional behavior for Noise / smoothing controls: Noise Reduction (Luminance), Noise Reduction (Color), Denoise Amount, Denoise Detail, Grain Reduction, Smoothing / Skin Smoothing

☐ Implement functional behavior for Dehaze / atmospheric controls: Dehaze, Haze Removal, Defog

☐ Implement functional behavior for Effects controls: Vignette, Fade, Grain, Glow / Bloom, Lens Blur, Motion Blur, Sharpen (Unsharp Mask), High Pass, Clarity/Pop

☐ Implement functional behavior for Brush controls: Enable toggle, Brush Size

☐ Implement functional behavior for Tone curve controls: Tone Curve (RGB), Channel Curves (R / G / B)

☐ Implement functional behavior for HSL / color mix controls: Hue (per color), Saturation (per color), Luminance (per color)

☐ Implement functional behavior for Color grading controls: Shadows Color, Midtones Color, Highlights Color, Balance, Split Toning (Highlight Hue/Sat, Shadow Hue/Sat)

☐ Implement functional behavior for Levels / channel controls: Levels (Input/Output), RGB Levels, Individual Channel Levels

☐ Implement functional behavior for Geometry / transform controls: Crop, Rotate, Straighten, Perspective (Vertical/Horizontal), Distort / Warp, Scale, Flip Horizontal / Vertical

☐ Implement functional behavior for any other existing visible edit control in the Full Image Viewer tab

☐ Implement non-destructive edit pipeline: edits apply to an in-memory working copy; original remains unchanged during editing; reset returns the working copy to the original state; undo/redo operates on the working copy

☐ Provide live preview for all edit controls using the working copy

☐ Add Output / Save Options section in the right-side settings rail with “Affect copy only / keep original” option (default enabled)

☐ Implement save workflow: default Save As (new file); overwrite original only with explicit user confirmation (checkbox or dialog); no silent overwrite

☐ Minimal UI changes limited to enabling existing controls and adding Output / Save Options as required

3. Out of Scope — Explicitly Forbidden Changes

List things that might be tempting but are not allowed.

Forbidden:

❌ Feature movement

❌ Renaming controls, variables, signals

❌ Logic or behavior changes outside the edit pipeline described in Scope

❌ Signal/handler rewiring unrelated to this DIFF

❌ Cleanup or refactors not explicitly listed

❌ Visual redesign beyond minimal UI changes required for Output / Save Options

❌ Changes to other tabs or global app behavior

❌ Changes to file scanning, metadata, or database workflows

❌ Automatic or silent overwrite of original files

Add any DIFF-specific exclusions here:

❌ New editing features not already present as visible controls in the Full Image Viewer tab

4. Implementation Rules (How work must be done)

Rules:

4.1 Standard Definitions

All controls must follow standard, industry-accepted photo editor behavior.

If a control name matches common photo editors, it must behave the same way.

No custom reinterpretations unless explicitly approved in a new DIFF.

4.2 Control Wiring

If a control exists visually, it must be wired and functional.

No placeholder or disabled stubs may remain.

4.3 Non-Destructive Workflow

Edits apply only to the in-memory working copy during editing.

Original file remains unchanged until a save action explicitly targets it.

Reset returns the working copy to the original state.

Undo/redo operates on the working copy.

4.4 Live Preview

All control changes must update the working copy preview immediately.

No control should require save to observe its effect.

4.5 Save Behavior

Default save action is Save As (new file).

Overwrite original is allowed only via explicit user confirmation (checkbox or dialog).

No silent overwrite under any circumstance.

“Affect copy only / keep original” must be visible, default enabled, and enforced.

4.6 UI Changes

UI changes must be minimal and limited to enabling existing controls and adding Output / Save Options in the right-side settings rail.

No layout redesign.

4.7 Implementation Directive

If behavior is unclear, follow standard photo editor behavior.

Do not pause implementation for philosophical ambiguity.

Any deviation must be documented and justified.

4.8 Stability

No crashes or freezes during normal editing, preview, or save operations.

5. DIFF-Scoped Tasks (Atomic, Taggable)

Break work into atomic tasks that can each be tagged.

Each task must be:

Small

Verifiable

Independently reversible

DIFF Tag	Task Description	File(s)	Notes
DIFF-003-001	Establish working-copy edit pipeline with live preview, reset, and undo/redo semantics	viewer.py + edit pipeline module (new/updated as needed)	Non-destructive base
DIFF-003-002	Implement Basic tone + Highlights/Shadows adjustments	viewer.py + edit pipeline module	Standard definitions
DIFF-003-003	Implement Color / white balance + HSL controls	viewer.py + edit pipeline module	Standard definitions
DIFF-003-004	Implement Detail/Sharpness + Texture/Micro-contrast controls	viewer.py + edit pipeline module	Standard definitions
DIFF-003-005	Implement Noise/Smoothing + Dehaze/Atmospheric + Effects controls	viewer.py + edit pipeline module	Standard definitions
DIFF-003-006	Implement Tone Curve + Levels/Channel + Color grading controls	viewer.py + edit pipeline module	Standard definitions
DIFF-003-007	Implement Geometry/Transform + Crop + Brush controls	viewer.py + edit pipeline module	Standard definitions
DIFF-003-008	Add Output / Save Options UI and enforce Save As default with explicit overwrite confirmation	viewer.py	Minimal UI change

6. Risk Assessment

Explain what could break and what must not break.

Risk Level: ☐ Low ☐ Medium ☑ High

Known Risks:

Live preview for many controls may introduce performance regressions or UI lag.

Incorrect processing could produce unexpected visual results versus standard definitions.

Save workflow changes could risk accidental overwrite if confirmation logic is wrong.

Must-Not-Break Behaviors:

Original image on disk must never change during editing.

No silent overwrite of original files.

App must remain responsive during slider changes and preview updates.

Existing image loading, viewing, and compare behaviors must continue to work.

7. Verification Checklist (MANDATORY)

All boxes must be checked before marking DIFF complete.

Structural Verification

☐ Only DIFF-scoped changes were made

☐ No changes outside allowed scope

☐ No forbidden actions occurred

☐ DIFF numbering and order respected

Functional Safety

☐ All existing visible edit controls in Full Image Viewer are functional

☐ All controls apply to the in-memory working copy only

☐ Live preview updates immediately on control changes

☐ Reset returns working copy to the original state

☐ Undo/redo operates on the working copy

☐ Default save action is Save As (new file)

☐ Overwrite original requires explicit confirmation and is never silent

☐ “Affect copy only / keep original” option is visible and default enabled

☐ No crashes or freezes during normal editing and saving

UI / Layout Verification (if applicable)

☐ UI changes limited to enabling existing controls and Output / Save Options section

☐ Output / Save Options appear in the right-side settings rail and are clearly labeled

Code Hygiene

☐ Every change is tagged with a DIFF tag

☐ No untagged edits

☐ Tags match this DIFF number

☐ Changes are logically grouped by tag

If any box is unchecked, the DIFF is not complete.

8. Agent Completion Report (Required)

To be filled by the implementing agent.

Summary of Changes:

DIFF Tags Implemented:

☐ DIFF-003-001

☐ DIFF-003-002

☐ DIFF-003-003

☐ DIFF-003-004

☐ DIFF-003-005

☐ DIFF-003-006

☐ DIFF-003-007

☐ DIFF-003-008

Verification Performed By Agent:

☐ Yes ☐ No

Agent Name: ____________________
Date: ____________________

Agent attests that changes were made only within DIFF scope.

9. Owner Acceptance & Lock

To be filled by the DIFF author / repo owner.

☐ Verification checklist reviewed

☐ Changes comply with DIFF intent

☐ No scope violations detected

DIFF Status Set To: ☐ Complete ☐ Locked

Owner Signature: ____________________
Date: ____________________

10. Post-Lock Rules

Once locked:

This DIFF may never be edited

Any follow-up requires a new DIFF

Reverts reference this DIFF number

End of DIFF-003
