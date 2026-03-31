## Development Workflow
- **Branching:** Create a unique feature branch for each task, named based on the task's context.
- **File Writes:** Apply all file changes directly to disk; do not wait for a diff popup confirmation.
- **Multi-Repo Scope:** You have access to both `ai_academy` and `ai_academy_frontend` within the `eduai` workspace. Always `cd` into the relevant directory before running git or build commands.
- **Brainstorming:** Before coding, summarize the task goals and identify potential edge cases. Unless I interrupt, proceed automatically to implementation.
- **Testing:** Write unit tests for every feature where possible. If a task is not testable, explicitly mention this during the brainstorming phase.
- **PR Cycle:** Once a task is complete, add .claude/TODO.md to git by marking the current task as checked/complete, then commit, push, and create a GitHub PR. Wait for my manual confirmation before starting the next task.
- **Revision Policy:** If changes are requested, provide them as new commits.
