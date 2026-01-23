# DIFF-001 — Global Layout Foundation (Spacing, Minimums, Resize Rules)

Status: ☐ In Progress ☐ Complete  
Depends on: DIFF-000 (Baseline UI Audit)  
Risk Level: Low (layout-only, no logic changes)

---

## Purpose

Establish a **global, enforceable layout foundation** that prevents overlap, unusable shrinking, and erratic resizing across the entire application.

DIFF-001 introduces:
- A single spacing system
- Minimum usable sizes
- Explicit resize priorities
- Base layout templates to be reused by all tabs

No features are moved.  
No logic is changed.  
No handlers are rewired.

---

## 1. Global Spacing System (Mandatory)

### DIFF-001-001: Introduce unified spacing constants

**What**
- Define one spacing scale used everywhere.

**Values (locked):**
- Outer padding: **16**
- Inter-section gap: **12**
- Within-section gap: **8**
- Property row height target: **30**
- Section header height target: **32**

**Where**
- Centralized UI constants module or top-level UI helper
- Reused by all `_apply_page_layout()` helpers

**Why**
- Eliminates inconsistent margins (40/28/etc.)
- Enables predictable visual rhythm

**Risk**
- Low (pure layout metrics)

---

## 5. Base Layout Templates (New Standard)

### DIFF-001-006: Introduce standard page skeletons

These are **patterns**, not widgets.

#### Template A — Tool Page with Primary Content

[ Header / Toolbar (fixed height) ]
[ Main Split ]
├─ Primary Content (Expanding)
└─ Right Rail (Bounded + Scroll)


#### Template B — Data / Batch Page

[ Control Bar (fixed) ]
[ Primary List / Table (Expanding) ]
[ Optional Logs / Results (Expanding or Split) ]

#### Template C — Settings Sub-Tab

[ Section Header ]
[ Scrollable Settings Body ]
[ Fixed Footer (Apply / Reset if present) ]

---

## DIFF-001 Declaration

> DIFF-001 establishes the global layout contract.
>  
> All subsequent DIFFs rely on these guarantees.
>  
> Any layout work after this point must conform to this foundation.

Signed: __________________________  
Date: ____________________________