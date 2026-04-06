---
name: weekly-review
description: End-of-week review — what got done, what's still open, lessons learned
emoji: "📊"
requires:
  tools: [task_list, note_list, note_search, recall_facts, remember_fact]
tags: [productivity, weekly]
---

# Weekly Review

## When to Use
When the user says "weekly review", "how was my week", "end of week", or "what did I accomplish".

## Workflow

### Step 1: Gather completed work
```
task_list(status="done")
```

### Step 2: Check what's still open
```
task_list(status="open")
```

### Step 3: Look for notes from this week
```
note_list()
note_search(query="this week")
```

### Step 4: Recall ongoing context
```
recall_facts(query="projects goals priorities commitments")
```

### Step 5: Write the review

```
## Weekly Review 📊

### ✅ Completed ([N] tasks)
[List done tasks, grouped by project]

### 🔄 Still in progress ([N] tasks)
[List open tasks — note any that have been open for a while]

### 📝 Notes created this week
[Note titles from note_list]

### 💡 Observations
[1-2 sentences: what went well, what kept slipping?]

### 🎯 Top 3 for next week
[Ask the user: "What are the 3 most important things for next week?"]
```

### Step 6: Save insights to memory
If the user shares lessons learned or priorities for next week, store them:
```
remember_fact(content="[insight or priority]", topic="weekly-review")
```

## Rules
- Use actual task data — never estimate counts or content
- Ask questions to prompt reflection, don't just dump data
- End by saving any new priorities the user mentions
