# TODO

Tasks for Claude. Each task has a status, optional priority, and optional notes.

## Status legend
- `[ ]` — to do
- `[~]` — in progress
- `[x]` — done
- `[-]` — cancelled

## Scope legend
- <F> - Frontend (React - ai_academy_frontend)
- <B> - Backend (Django - ai_academy)

## Priority legend (optional)
- `!` — low
- `!!` — medium
- `!!!` — high / urgent


---

## Template

```
- [ ] [!!] Short task title <F> <B>
  - Context: which project / file / area this touches
  - Notes: any extra detail Claude needs to do this well
```

## UI Template

```
- [ ] [!!] Page/component name <F>
  - Context: which page, route, or component area this belongs to
  - Layout: describe the overall structure (columns, panels, sections)
  - Components:
    - List each visual element and its behaviour
    - List each interactive element and what it does on click/hover/etc.
  - Data: what API endpoints or state this depends on
  - Edge cases: empty states, loading, errors, permissions
  - Notes: any extra detail (style references, similar existing components, etc.)
```

---

## Backlog

<!-- Add tasks below. Claude will pick them up top-to-bottom unless priority says otherwise. -->

- [ ] Live classes <F> <B> — Classroom rendered with chair sits and one desk at top for the professor.
 - Context: apps/liveclasses + new React page
 - Components:
   - Classroom
   - student table
   - professor table
   - ai mac mini looking character
   - ai professor character
   - student character (with an ability to randomize unique colors)
   - chat window
   - chat tabs
 - Notes:
   - Classroom UI: chairs for students, professor desk at top
   - Only show present/active students (signed into the room); assign them to seats
   - Absent/disconnected students get an online status badge
   - Click student → opens chat window; minimizable as tabs at bottom
   - Click professor desk → same chat behavior
   - AI widget on professor's desk (mac mini style); click → AI chat (scoped to course policies)
   - If professor absent → AI moves to professor's chair, mac mini stays, but AI profesors can answer what the professor would
   - Make all the API endpoint views/serializers/models in DRF as needed by the UI needs
