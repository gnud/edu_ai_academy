# Semester — Business Rules

A `Semester` is a time-bound instance of a `Course`. While a `Course` is a reusable template (title, description, curriculum, policy), a `Semester` represents a concrete run of that course for a specific group of students during a specific period.

---

## Model Fields

| Field            | Type             | Notes                                              |
|------------------|------------------|----------------------------------------------------|
| `course`         | FK → Course      | The course this semester belongs to                |
| `name`           | CharField        | e.g. "Spring 2025", "Cohort 3"                     |
| `max_students`   | PositiveIntegerField (nullable) | Capacity cap for this run. Null = unlimited |
| `starts_on`      | DateField        | Semester start date                                |
| `ends_on`        | DateField (nullable) | Semester end date. Null = open-ended           |
| `enrollment_open`| BooleanField     | Whether new students can enroll                    |
| `status`         | SemesterStatus   | See statuses below                                 |

---

## Statuses

| Status      | Meaning                                                  |
|-------------|----------------------------------------------------------|
| `scheduled` | Future semester — dates confirmed, not yet started       |
| `active`    | Currently running — only one allowed per course at once  |
| `completed` | Finished — historical record, no restrictions            |
| `cancelled` | Cancelled — historical record, no restrictions           |

---

## Validation Rules

### Rule 1 — One active semester per course

A course can have **at most one `active` semester** at any point in time.

- Attempting to set a second semester to `active` on the same course raises a validation error.
- `completed` and `cancelled` semesters are not affected by this rule.

### Rule 2 — No date overlap between active and scheduled semesters

When a semester is `active` or `scheduled`, its date range must not overlap with any other `active` or `scheduled` semester on the same course.

**Overlap definition:** Two date ranges `[s1, e1]` and `[s2, e2]` overlap unless one ends strictly before the other starts:
- No conflict if `other.ends_on < self.starts_on` (other ends before self starts)
- No conflict if `self.ends_on < other.starts_on` (self ends before other starts)

**Open-ended semesters** (`ends_on = null`) are treated as running indefinitely. An open-ended semester conflicts with any other active/scheduled semester whose `starts_on` falls on or after its own `starts_on`.

**Examples:**

| Existing semester       | New semester attempt     | Result  |
|-------------------------|--------------------------|---------|
| Active: Jan–Jun 2025    | Scheduled: Apr–Sep 2025  | ❌ Blocked (overlap) |
| Active: Jan–Jun 2025    | Scheduled: Jul–Dec 2025  | ✅ Allowed (no overlap) |
| Active: Jan–Jun 2025    | Scheduled: Jun–Dec 2025  | ❌ Blocked (same end/start = overlap) |
| Scheduled: Jan–Jun 2026 | Scheduled: May–Oct 2026  | ❌ Blocked (overlap) |
| Scheduled: Jan–Jun 2026 | Scheduled: Jul–Dec 2026  | ✅ Allowed (no overlap) |
| Active: Jan–null (open) | Scheduled: Mar 2025–null | ❌ Blocked (open-ended conflicts with anything starting after Jan) |
| Completed: Jan–Jun 2025 | Scheduled: Apr–Sep 2025  | ✅ Allowed (completed is excluded from checks) |
| Cancelled: Jan–Jun 2025 | Scheduled: Apr–Sep 2025  | ✅ Allowed (cancelled is excluded from checks) |

### Rule 3 — Inline creation with a new course skips DB checks

When a `Semester` is created inline alongside a brand-new `Course` (before the parent is saved), `course_id` is `None` and no DB queries are possible. Validation is skipped in this case — the semester is the first and only one for that course at that point, so no conflicts can exist.

### Rule 4 — Completed and cancelled are immutable historically

Semesters in `completed` or `cancelled` status are excluded from all overlap and uniqueness checks. They serve as historical records and must not be modified to affect running or future semesters.

---

## Service Layer

Business logic is centralised in `apps/academy/services.py` and must be called from every interface (admin, API, management commands) rather than relying solely on model-level saves.

| Function                        | Purpose                                                                                      |
|---------------------------------|----------------------------------------------------------------------------------------------|
| `save_semester(obj)`            | Runs `full_clean()` (triggers all rules above) then saves. Use in API and non-admin contexts. |
| `save_course(obj, user, change)`| Sets `created_by` on creation, then saves.                                                   |

The Django admin calls `Semester.clean()` automatically during form validation, so errors surface in the UI before save. For all other interfaces, `save_semester()` ensures the same rules are enforced.