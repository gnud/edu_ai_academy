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

- [x] Live classes <F> <B> — Classroom rendered with chair sits and one desk at top for the professor.
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

- [x] Live classes <B> — Management command to seed scheduled classrooms (few at Now, more items at next days in the week), semester data, for all users
or argument flag to select for which users to be mandatorily included 
 - Context: apps/liveclasses

- [x] Live classes <F> <B> — Chat window left and right directions for participants
 - Context: apps/liveclasses + update frontend chat
 - Components:
   - chat window
   - chat block
 - Notes:
   - Make sure the left side shows the other chat participant and right are sender messages, each message uses a chat block component
   - Make sure the chat block component allows colors if more than one receiver aka left side
   - Make sure the chat block component shows a timestamp and participant avatar + name if more than one participant
   - Make sure the chat block component shows badge of roles type: professor, admin, support, ai bot

- [x] Live classes <F> <B> — Chat window group participants
  - Context: apps/liveclasses + update frontend chat
  - Components:
   - chat window
   - sticky Tab group manager
   - stats list
 - Notes:
   - A professor signed in Live Classes can select the student's tables and group them
   - A toolbar with actions, group button
   - Clicking "Group button"
     - will open a group manager, where professor can create a new group
     - and add available students
     - and set group mode active, also displayed in the status list
   - Groups will be accessible as a sticky tab at the Page right side middle, clicking it will open list of groups and count badge
   - Group button changes to Ungroup or Deactivate Grouping upon you want to stop the group mode, the groups tab is disabled 
   - Banner on top/right states grouping active and other stats, total students, current professor, count of absent students
   - Groups have chat windows with multiple members, note the badges for roles to distinguish students and professors and others

- [x] Live classes <F> <B> — BUG fix: Chat window group participants
  - Context: apps/liveclasses + update frontend chat
 - Notes:
   - Below the class room tables there is Groups island, get rid of it
   - kick is not working: "[31/Mar/2026 17:40:58] "DELETE /api/classes/Z/groups/X/members/Y/ HTTP/1.1" 404" backend API call not implemented

- [x] Live classes <F> <B> — Blackboard
  - Components:
    - Blackboard
    - Filemanager
    - Control Toolbar
  - Context: apps/liveclasses + blackboard slideshow
 - Notes:
   - Create a file manager where professor/staff can upload files (text, markdown, pdf, videos, music, images)
   - Upon clicking on the blackboard professor/staff blackboard goes fullscreen, and staff can select files from the file manager on the left
   and clicking the file loads it in the blackboard
   - Blackboard toolbar buttons (Control Toolbar)
       - Start — will make sure all participants will activate the blackboard in fullscreen
       - Stop — will make sure all participants will deactivate fullscreen
       - Broadcast - will emit currently selected file, the broadcast file will have a Live icon on it
       - Scroll buttons - up/down will emit commands to the blackboard among all the participants to vertically scroll the file content
       - Zoom/"Zoom out" - for images only and PDF and text
       - Play/Pause - for videos/music only
       - Rotate - only fHoor images/pdf
   - Rules: Students may not exit fullscreen
