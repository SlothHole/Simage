DIFF-XXX — <Short, Precise Title>

Status: ☐ Draft ☐ In Progress ☐ Complete ☐ Locked
Depends on: DIFF-<previous>
Risk Level: ☐ Low ☐ Medium ☐ High

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

Describe exactly why this change is needed.

Rules:

One paragraph maximum

No solutions here

No implementation detail

No future-looking statements

Purpose:

2. Scope — Explicitly Allowed Changes

List only what may be changed.

Rules:

Use bullet points

Be concrete

If it’s not here, it’s forbidden

Allowed:

☐ ______________________________________

☐ ______________________________________

☐ ______________________________________

3. Out of Scope — Explicitly Forbidden Changes

List things that might be tempting but are not allowed.

Forbidden:

❌ Feature movement

❌ Renaming controls, variables, signals

❌ Logic or behavior changes

❌ Signal/handler rewiring

❌ Cleanup or refactors not explicitly listed

❌ Visual redesign (unless stated in Scope)

Add any DIFF-specific exclusions here:

❌ ______________________________________

❌ ______________________________________

4. Implementation Rules (How work must be done)

Rules that govern execution, not goals.

Examples:

Layout containers may be added, but existing widgets must not be recreated

Controls must be re-parented, not replaced

Existing persistence keys must remain unchanged

Minimum sizes must be enforced before splitter persistence

Rules:

5. DIFF-Scoped Tasks (Atomic, Taggable)

Break work into atomic tasks that can each be tagged.

Each task must be:

Small

Verifiable

Independently reversible

DIFF Tag	Task Description	File(s)	Notes
DIFF-XXX-001			
DIFF-XXX-002			
DIFF-XXX-003			
6. Risk Assessment

Explain what could break and what must not break.

Risk Level: ☐ Low ☐ Medium ☐ High

Known Risks:

Must-Not-Break Behaviors:

7. Verification Checklist (MANDATORY)

All boxes must be checked before marking DIFF complete.

Structural Verification

☐ Only DIFF-scoped changes were made

☐ No changes outside allowed scope

☐ No forbidden actions occurred

☐ DIFF numbering and order respected

Functional Safety

☐ No feature behavior changed

☐ No logic or signal wiring changed

☐ Existing persistence/settings preserved

☐ No regressions observed

UI / Layout Verification (if applicable)

☐ No control overlap at any window size

☐ No control shrinks below usable size

☐ Primary content expands before secondary panels

☐ Secondary panels scroll instead of compress

☐ Resize behavior is predictable

☐ No visual breakage at minimum size

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

☐ DIFF-XXX-001

☐ DIFF-XXX-002

☐ DIFF-XXX-003

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

End of DIFF-XXX