"""Memo tools — note and task management backed by plain JSON/Markdown files.

Data layout under MEMO_DATA_DIR (default: ~/.local/share/memo):
  notes/
    <slug>.md          # one file per note, YAML frontmatter + body
  tasks/
    tasks.json         # single JSON array of task objects
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Data directory
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    base = Path(os.environ.get("MEMO_DATA_DIR", Path.home() / ".local/share/memo"))
    (base / "notes").mkdir(parents=True, exist_ok=True)
    (base / "tasks").mkdir(parents=True, exist_ok=True)
    return base


def _slug(title: str) -> str:
    """Convert a note title to a safe filename."""
    return re.sub(r"[^\w\-]", "-", title.lower().strip()).strip("-")


# ---------------------------------------------------------------------------
# Note tools
# ---------------------------------------------------------------------------

@tool
def note_create(title: str, content: str, tags: str = "") -> str:
    """Create or overwrite a note.

    title: human-readable title (becomes the filename)
    content: the note body (Markdown)
    tags: comma-separated tags, e.g. "work,ideas"
    Returns the path where the note was saved.
    """
    path = _data_dir() / "notes" / f"{_slug(title)}.md"
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    frontmatter = (
        f"---\n"
        f"title: {title}\n"
        f"tags: [{', '.join(tag_list)}]\n"
        f"created: {datetime.now().isoformat(timespec='seconds')}\n"
        f"---\n\n"
    )
    path.write_text(frontmatter + content, encoding="utf-8")
    return f"Note saved: {path}"


@tool
def note_read(title: str) -> str:
    """Read a note by title. Returns the full content including frontmatter."""
    path = _data_dir() / "notes" / f"{_slug(title)}.md"
    if not path.exists():
        return f"Note not found: {title!r}. Use note_list() to see available notes."
    return path.read_text(encoding="utf-8")


@tool
def note_search(query: str) -> str:
    """Search all notes for a keyword or phrase (case-insensitive).

    Returns matching note titles and a short snippet around the match.
    """
    notes_dir = _data_dir() / "notes"
    query_lower = query.lower()
    results: list[str] = []

    for path in sorted(notes_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if query_lower in text.lower():
            # Extract a snippet around the first match
            idx = text.lower().find(query_lower)
            start = max(0, idx - 60)
            snippet = text[start : idx + 120].replace("\n", " ").strip()
            results.append(f"• {path.stem}: ...{snippet}...")

    if not results:
        return f"No notes found matching {query!r}."
    return f"Found {len(results)} note(s):\n" + "\n".join(results)


@tool
def note_list(tag: str = "") -> str:
    """List all notes, optionally filtered by tag.

    Returns note titles, tags, and creation dates.
    """
    notes_dir = _data_dir() / "notes"
    lines: list[str] = []

    for path in sorted(notes_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        # Parse frontmatter tags line
        tags_match = re.search(r"^tags:\s*\[([^\]]*)\]", text, re.MULTILINE)
        note_tags = tags_match.group(1) if tags_match else ""
        title_match = re.search(r"^title:\s*(.+)", text, re.MULTILINE)
        note_title = title_match.group(1).strip() if title_match else path.stem

        if tag and tag.lower() not in note_tags.lower():
            continue
        lines.append(f"• {note_title}" + (f"  [{note_tags}]" if note_tags else ""))

    if not lines:
        return "No notes found." if not tag else f"No notes with tag {tag!r}."
    return f"{len(lines)} note(s):\n" + "\n".join(lines)


@tool
def note_delete(title: str) -> str:
    """Permanently delete a note. This cannot be undone."""
    path = _data_dir() / "notes" / f"{_slug(title)}.md"
    if not path.exists():
        return f"Note not found: {title!r}"
    path.unlink()
    return f"Deleted: {title}"


# ---------------------------------------------------------------------------
# Task tools
# ---------------------------------------------------------------------------

def _load_tasks() -> list[dict]:
    path = _data_dir() / "tasks" / "tasks.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_tasks(tasks: list[dict]) -> None:
    path = _data_dir() / "tasks" / "tasks.json"
    path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")


@tool
def task_add(title: str, project: str = "personal", due_date: str = "") -> str:
    """Add a new task.

    title: what needs to be done
    project: which project it belongs to (default: "personal")
    due_date: optional ISO date string, e.g. "2026-04-10"
    """
    tasks = _load_tasks()

    # Validate due_date if provided
    if due_date:
        try:
            date.fromisoformat(due_date)
        except ValueError:
            return f"Invalid due_date {due_date!r} — use ISO format: YYYY-MM-DD"

    task = {
        "id": len(tasks) + 1,
        "title": title,
        "project": project,
        "due_date": due_date,
        "status": "open",
        "created": datetime.now().isoformat(timespec="seconds"),
        "done_at": None,
    }
    tasks.append(task)
    _save_tasks(tasks)

    due = f" (due {due_date})" if due_date else ""
    return f"Task added: [{project}] {title}{due}"


@tool
def task_list(project: str = "", status: str = "open") -> str:
    """List tasks, optionally filtered by project and status.

    status: "open" (default) | "done" | "all"
    project: filter by project name (leave empty for all projects)
    """
    tasks = _load_tasks()

    if status != "all":
        tasks = [t for t in tasks if t["status"] == status]
    if project:
        tasks = [t for t in tasks if t["project"] == project]

    if not tasks:
        label = f"[{project}] " if project else ""
        return f"No {label}{status} tasks."

    today = date.today().isoformat()
    lines: list[str] = []
    for t in tasks:
        check = "✓" if t["status"] == "done" else "○"
        due = ""
        if t.get("due_date"):
            overdue = t["status"] == "open" and t["due_date"] < today
            due = f" ({'OVERDUE: ' if overdue else 'due '}{t['due_date']})"
        lines.append(f"{check} [{t['project']}] {t['title']}{due}")

    header = f"{len(tasks)} {status} task(s)" + (f" in {project}" if project else "")
    return f"{header}:\n" + "\n".join(lines)


@tool
def task_done(title: str) -> str:
    """Mark a task as complete by title (partial match is fine).

    Returns confirmation or a list of matches if the title is ambiguous.
    """
    tasks = _load_tasks()
    title_lower = title.lower()
    matches = [t for t in tasks if title_lower in t["title"].lower() and t["status"] == "open"]

    if not matches:
        return f"No open task found matching {title!r}."
    if len(matches) > 1:
        options = "\n".join(f"  • {t['title']}" for t in matches)
        return f"Multiple matches — be more specific:\n{options}"

    matches[0]["status"] = "done"
    matches[0]["done_at"] = datetime.now().isoformat(timespec="seconds")
    _save_tasks(tasks)
    return f"Done: {matches[0]['title']} ✓"


@tool
def task_delete(title: str) -> str:
    """Permanently remove a task by title."""
    tasks = _load_tasks()
    before = len(tasks)
    tasks = [t for t in tasks if t["title"].lower() != title.lower()]
    if len(tasks) == before:
        return f"Task not found: {title!r}"
    _save_tasks(tasks)
    return f"Deleted task: {title}"
