# DIFF PROCESS — CHANGE GOVERNANCE STANDARD

## Purpose

This repository uses a **DIFF-governed change system** to ensure that all modifications are:

- Intentional
- Auditable
- Reversible
- Scoped
- Safe to execute by humans or agents

This document defines **what a DIFF is**, **how DIFFs are created**, **who is allowed to do what**, and **how changes move from idea to implementation**.

---

## 1. What a DIFF Is

A **DIFF** is a **versioned change contract**.

A DIFF defines:
- What is allowed to change
- What is forbidden to change
- Why the change exists
- How completion is verified
- Who authorizes the change

A DIFF is **not**:
- A code diff
- A suggestion
- A TODO list
- A design brainstorm

A DIFF is **authoritative scope control**.

---

## 2. DIFF Numbering & Types

### DIFF numbering rules

- DIFFs are numbered sequentially:
  - `DIFF-000`
  - `DIFF-001`
  - `DIFF-002`
  - …

Rules:
- Numbers are **monotonic**
- Numbers are **never reused**
- Numbers are **never inserted retroactively**
- Locked DIFFs are **never edited**

---

### DIFF-000 (Baseline)

**DIFF-000 is special.**

Purpose:
- Capture the factual baseline of the system *before any changes*

Rules:
- No changes allowed
- No prescriptions
- No “should” language
- UNKNOWN is acceptable
- Facts only

DIFF-000 exists to:
- Freeze reality
- Separate pre-existing behavior from regressions
- Protect future changes from blame ambiguity

DIFF-000 is written and signed **only by the repo owner**.

---

### Change-bearing DIFFs (DIFF-001+)

All DIFFs after DIFF-000 introduce scoped changes.

They must:
- Be explicit
- Be limited in scope
- Be independently verifiable
- Build on previous DIFFs

---

## 3. DIFF Lifecycle

Every DIFF follows this lifecycle:

Draft → In Progress → Complete → Locked

### Lifecycle meanings

- **Draft**
  - Intent is being defined
  - No implementation allowed

- **In Progress**
  - DIFF scope is frozen
  - Implementation may begin

- **Complete**
  - All verification criteria satisfied
  - Awaiting owner acceptance

- **Locked**
  - DIFF is finalized
  - May never be edited
  - Any follow-up requires a new DIFF

---

## 4. Roles & Responsibilities

### Repo Owner (You)

- Defines intent
- Authors DIFFs
- Approves scope
- Verifies completion
- Locks DIFFs
- Signs DIFF documents

The repo owner is the **sole authority** on scope.

---

### Implementers (Humans or Agents)

- Execute only what the DIFF specifies
- Do not reinterpret intent
- Do not expand scope
- Tag all changes with DIFF identifiers
- Report completion — **do not authorize it**

Implementers **never sign DIFFs**.

---

## 5. Scope Discipline (Critical)

### Allowed by default
- Nothing

Only changes **explicitly listed** in the active DIFF are allowed.

---

### Forbidden by default
Unless explicitly permitted, the following are forbidden:

- Feature movement
- Renaming
- Logic or behavior changes
- Signal/handler rewiring
- Refactors
- Cleanup
- “Improvements”
- Styling or redesign

If an implementer believes a forbidden change is required:
> They must STOP and ASK.

Guessing intent is a hard failure.

---

## 6. DIFF Authoring Requirements

Every DIFF must include:

1. Purpose
2. Explicit scope (allowed changes)
3. Explicit out-of-scope list
4. Implementation rules
5. Risk assessment
6. Verification checklist
7. Declaration
8. Owner acceptance section

A DIFF missing any of these sections is invalid.

---

## 7. DIFF Tagging in Code

All code changes must be tagged inline:

```python
# DIFF-001-004: Enforce minimum window size
Rules:

One logical change = one DIFF tag

No untagged changes

Tags must match the active DIFF

This enables:

Audits

Reverts

Accountability

Multi-agent coordination

8. Verification & Acceptance
A DIFF is not complete until:

All verification checklist items are satisfied

No scope violations are detected

Repo owner explicitly accepts the DIFF

Unchecked verification items block progression to the next DIFF.

9. Multi-Agent & Multi-Contributor Rules
Only one active DIFF at a time

All implementers work against the same DIFF

No preparatory work for future DIFFs

No speculative changes

DIFFs serialize work intentionally.

10. Failure Conditions
Any of the following invalidates work:

Changing code outside DIFF scope

Editing a locked DIFF

Skipping or reordering DIFFs

Missing DIFF tags

Guessing intent

Mixing DIFFs in one implementation pass

Invalid work must be reverted or redone under a new DIFF.

11. Repository Structure (Recommended)
powershell
Copy code
/diffs/
  DIFF-000.md
  DIFF-001.md
  DIFF-002.md

/docs/
  DIFF_PROCESS.md
  DIFF_TEMPLATE.md
  AGENT_PROMPT.md
12. Final Principle
Intent is owned by the author.
Execution is owned by the implementer.
Authority remains with the DIFF.

This process exists to keep changes controlled, provable, and reversible — even when multiple agents or contributors are involved.

End of DIFF_PROCESS.md