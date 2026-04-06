---
name: daily-briefing
description: Morning overview — open tasks, overdue items, and what to focus on today
emoji: "☀️"
requires:
  tools: [task_list, note_search, recall_facts]
tags: [productivity, daily]
---

# Daily Briefing

## When to Use
When the user says "good morning", "what's on today", "brief me", "daily briefing", or similar.

## Workflow

### Step 1: Recall user context
```
recall_facts(query="current priorities projects goals")
```

### Step 2: Check open tasks
```
task_list(status="open")
```

### Step 3: Check for overdue items
The `task_list` output flags overdue tasks automatically. Note any that are past their due date.

### Step 4: Check recent notes
```
note_search(query="today")
note_search(query="urgent")
```

### Step 5: Compose the briefing

Use this format — keep it scannable, under 20 lines total:

```
## Good morning! ☀️

### 🎯 Focus for today
[One thing the user should prioritise — based on overdue tasks or recalled context]

### 📋 Open tasks  ([N] total)
[List open tasks, overdue ones first with ⚠️]

### 📝 Recent notes
[Any notes tagged "today" or containing "urgent", if found]

### 💬 Anything to add?
[Ask if they want to add tasks or notes for today]
```

If there are no open tasks, say so cheerfully and ask what they're working on today.

## Rules
- Never invent tasks — only report what `task_list` returns
- Highlight overdue tasks clearly
- Keep the tone energetic but not exhausting
