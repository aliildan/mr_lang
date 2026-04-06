---
name: quick-capture
description: Fast capture mode — save a note or task with minimal friction
emoji: "⚡"
requires:
  tools: [note_create, task_add, remember_fact]
tags: [capture, quick]
---

# Quick Capture

## When to Use
When the user wants to capture something fast — especially from Telegram on the go. Trigger phrases:
- "note: ..."
- "task: ..."
- "remember: ..."
- "add: ..."
- A message that starts with a verb ("Buy milk", "Fix login bug", "Write proposal")

In quick-capture mode: **act first, confirm after**. Don't ask clarifying questions before saving.

## Decision Logic

| Input pattern | Action |
|--------------|--------|
| "note: [text]" | `note_create` with the text as both title (first line) and content |
| "task: [text]" | `task_add` with the text as title |
| "remember: [text]" | `remember_fact` to store a persistent fact |
| Imperative phrase (Buy, Fix, Call, Write...) | `task_add` — interpret as a task |
| Longer paragraph or structured text | `note_create` |

## Workflow

### Step 1: Parse the input
- Extract the title (first sentence or phrase)
- Detect any project name: "for work", "personal", "re: [project]"
- Detect any due date: "by Friday", "tomorrow", "2026-04-10"

### Step 2: Save immediately
```
# For a task:
task_add(title="Fix login bug", project="work", due_date="2026-04-10")

# For a note:
note_create(title="Meeting notes", content="...", tags="work,meetings")

# For a persistent fact:
remember_fact(content="Prefers Python examples in explanations", topic="preferences")
```

### Step 3: Confirm in one line
```
✓ Task added: [Fix login bug] (work, due Apr 10)
✓ Note saved: Meeting notes [work, meetings]
✓ Remembered: Prefers Python examples
```

Never reply with more than one line in quick-capture mode unless clarification is genuinely needed.

## Rules
- Speed over perfection — save now, refine later
- If the project is unclear, default to "personal"
- If the due date is unclear, leave it empty
- Don't ask "are you sure?" for captures — just do it
