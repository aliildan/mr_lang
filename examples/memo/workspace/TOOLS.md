# Tools

All data is stored under `MEMO_DATA_DIR` (default: `~/.local/share/memo`).

## Notes

- `note_create(title, content, tags)` — Create or overwrite a note. Tags are comma-separated (e.g. `"work,ideas"`).
- `note_read(title)` — Read a note by title.
- `note_search(query)` — Full-text search across all notes. Returns matching titles and snippets.
- `note_list(tag)` — List all notes, optionally filtered by tag.
- `note_delete(title)` — Delete a note permanently (ask user to confirm first).

## Tasks

- `task_add(title, project, due_date)` — Add a task. `due_date` is optional (ISO format: `2026-04-10`).
- `task_list(project, status)` — List tasks. `status`: `open` (default) | `done` | `all`. `project` is optional.
- `task_done(title)` — Mark a task as complete.
- `task_delete(title)` — Delete a task (ask user to confirm first).

## Memory (built-in)

- `remember_fact(content, topic)` — Store a persistent fact about the user or their context.
- `recall_facts(query)` — Retrieve stored facts relevant to a query.
- `forget_fact(fact_id)` — Remove a stored fact.

## Knowledge Base (built-in)

- `search_knowledge(query)` — Semantic search over indexed documents.
- `add_to_knowledge(content, source)` — Index new content into the knowledge base.

## File System (built-in)

- `read_file(path)` — Read any file.
- `list_files(path, pattern)` — List files matching a glob pattern.
