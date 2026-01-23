# DIFF-000 — Baseline UI Audit Worksheet

Status: ☐ In Progress ☑ Complete  
Auditor(s): ChatGPT (file-driven UI audit)  
Date Started: 2026-01-23  
Date Completed: 2026-01-23  

> DIFF-000 captures the factual baseline of the UI before any layout or UX changes.
> No behavior, logic, or visual modifications are permitted during this phase.

---

## 1. Application-wide Baseline

### 1.1 Root Window & Layout

- Root window type / class:
  - `SimageUIMain(QMainWindow)` (app.py)

- Central widget:
  - `QTabWidget` assigned via `self.setCentralWidget(self.tabs)` (app.py)

- Tab order (as built in code):
  - Gallery & Search → Tag Images → Edit Images → Batch Processing → Settings → Full Image Viewer → DB Viewer (app.py)

- Root layout container(s):
  - QMainWindow (central widget: QTabWidget)
  - Each tab uses its own layout (mostly QVBoxLayout/QHBoxLayout + QSplitter/QTabWidget)

- Uses absolute/manual positioning anywhere?
  - ☐ Yes ☑ No ☐ Unknown
  - Notes:
    - Repo-wide scan found no usage of `.setGeometry()` or `.move()`.
    - All positioning is handled via Qt layout managers.

- Current resize behavior:
  - ☐ Fixed
  - ☑ Partial
  - ☐ Fully resizable
  - Notes:
    - Window is resizable (explicit `resize(1600, 1000)`).
    - Code intentionally sets minimum sizes to 0 and uses `QSizePolicy(Ignored)` in several places, allowing aggressive shrinking.

- Minimum window size defined?
  - ☑ Yes ☐ No ☐ Unknown
  - Value:
    - `QMainWindow.setMinimumSize(0, 0)` (app.py)

- Global padding/margin behavior:
  - ☐ Consistent
  - ☑ Inconsistent
  - ☐ Unknown
  - Notes:
    - `_apply_page_layout()` commonly uses margins `(40,40,40,40)` and spacing `28`.
    - GalleryTab uses a separate helper with potentially different values.

---

### 1.2 Global Layout Risk Scan

| Risk Condition | Yes | No | Unknown | Notes |
|---------------|-----|----|---------|-------|
| Control overlap at small sizes | ☐ | ☐ | ☑ | Not stress-tested; aggressive shrinking enabled globally. |
| Controls shrink below usability | ☑ | ☐ | ☐ | `setMinimumSize(0,0)` and `QSizePolicy(Ignored)` are applied broadly. |
| Entire tabs do not resize | ☐ | ☑ | ☐ | Layout managers and splitters are used throughout. |
| Everything stretches uniformly | ☐ | ☐ | ☑ | Depends on tab-specific policies. |
| Empty space consumed by controls | ☑ | ☐ | ☐ | Large margins and `addStretch(1)` observed in multiple layouts. |
| Only window-level scrolling | ☐ | ☑ | ☐ | Panel-level scroll exists in some tabs (Edit, Settings custom colors). |

---

## 8. DIFF-000 Completion Gate

- ☑ All tabs audited
- ☑ All primary content identified
- ☑ Initial high-risk containers logged
- ☑ No assumptions left undocumented
- ☑ DIFF-000 ready for completion

---

## DIFF-000 Declaration

> DIFF-000 establishes the authoritative UI baseline.
>  
> All behavior described herein is considered **pre-existing**.
>  
> No layout, UX, or behavior changes were performed.

Signed: ___SlothBucket______ 2026-01-23_03:48:00 
Date: 2026-01-23
