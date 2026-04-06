---
name: add-workspace
description: Scaffold a new workspace directory with IDENTITY/SOUL/USER/TOOLS/AGENTS template files
---

# Add Workspace

Create a new workspace for the mr_lang framework. A workspace defines an agent's complete personality, knowledge, and capabilities through Markdown files.

## Instructions

When the user asks to create a new workspace, follow these steps:

1. Ask for the workspace name, agent purpose, and target language(s) if not provided
2. Create the workspace directory at the requested path (or `examples/workspaces/<name>/`)
3. Create all 5 workspace files with content tailored to the use case

## Files to Create

### IDENTITY.md (required)
```markdown
# Identity

- **Name**: <Agent Name>
- **Role**: <What the agent does, e.g., "Math tutor for secondary school students">
- **Language**: <Primary language(s), e.g., "German">
- **Version**: 0.1.0
```

### SOUL.md
```markdown
# Personality & Rules

## Personality
<Describe tone, communication style — be specific and actionable>

## Core Rules
1. <Rule about behavior, e.g., "Never give direct answers — guide with questions">
2. <Rule about boundaries, e.g., "Stay on topic, redirect off-topic questions">
3. <Rule about format, e.g., "Use bullet points for lists, code blocks for code">

## Interaction Style
- <How the agent greets users>
- <How it handles errors or unknowns>
- <How it asks for clarification>
```

### USER.md
```markdown
# User Profile

## Target Audience
<Who uses this agent, e.g., "14-16 year old students in Austrian schools">

## Context
<What the user needs help with>

## Preferences
- <Language preferences>
- <Detail level preferences>
- <Format preferences>
```

### TOOLS.md
```markdown
# Available Tools

## System Tools
- `read_file` — Read files from the filesystem
- `write_file` — Write files to the filesystem
- `list_files` — List directory contents
- `run_shell` — Execute shell commands

## Memory Tools
- `remember_fact` — Store a fact for future reference
- `recall_facts` — Search memory for relevant facts
- `forget_fact` — Remove a stored fact

## Custom Tools
<List plugin-specific tools here>
```

### AGENTS.md
```markdown
# Agent Configuration

## Primary Agent
- **Provider**: <ollama|openai|anthropic>
- **Model**: <model name>
- **Temperature**: 0.7
```

## How Workspaces Are Used

1. `load_workspace(path)` reads all `.md` files from the directory
2. `build_system_prompt(ws)` concatenates them with section separators into one system message
3. The system prompt is passed to `build_agent_graph()` and prepended to every model call
4. Skills are appended after the workspace content

## Rules

- All files are Markdown — no YAML/JSON config in the workspace
- IDENTITY.md is the only required file; others are optional but recommended
- Workspace directory name should be kebab-case or snake_case
- Keep SOUL.md focused — overly long personality rules degrade agent performance
- AGENTS.md content is now included in the system prompt (via `build_system_prompt`)
- When used with a plugin, set `workspace_dir` in `mr_lang_plugin.toml`:
  ```toml
  [plugin.paths]
  workspace = "./workspace"
  ```
- The `--workspace` CLI flag overrides the plugin's workspace path
