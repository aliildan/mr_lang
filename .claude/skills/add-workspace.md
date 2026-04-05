---
name: add-workspace
description: Scaffold a new workspace directory with IDENTITY/SOUL/USER/TOOLS/AGENTS template files
---

# Add Workspace

Create a new workspace for the mr_lang framework. A workspace defines an agent's complete personality, knowledge, and capabilities through Markdown files.

## Instructions

When the user asks to create a new workspace, follow these steps:

1. Ask for the workspace name, agent purpose, and target language(s) if not provided
2. Create the workspace directory at `examples/workspaces/<name>/` (or custom path)
3. Create all 5 workspace files with sensible defaults

## Files to Create

### IDENTITY.md
```markdown
# Identity

- **Name**: <Agent Name>
- **Role**: <What the agent does>
- **Language**: <Primary language(s)>
- **Version**: 0.1.0
```

### SOUL.md
```markdown
# Personality & Rules

## Personality
<Describe the agent's personality, tone, communication style>

## Core Rules
1. <Rule about behavior>
2. <Rule about boundaries>
3. <Rule about output format>

## Interaction Style
- <How the agent greets users>
- <How it handles errors or unknowns>
- <How it asks for clarification>
```

### USER.md
```markdown
# User Profile

## Target Audience
<Who uses this agent>

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
- `read_file` — Read files from the workspace
- `write_file` — Write files to the workspace
- `shell` — Execute shell commands

## Custom Tools
<List project-specific tools here>

## Environment
<Required environment variables and setup>
```

### AGENTS.md
```markdown
# Agent Configuration

## Primary Agent
- **Model**: ollama/llama3
- **Provider**: ollama
- **Temperature**: 0.7

## Sub-Agents
<Define specialized sub-agents if needed>
```

## Rules

- All files are Markdown — no YAML/JSON config files in workspace
- IDENTITY.md is required, others are optional but recommended
- Workspace directory name should be kebab-case or snake_case
- The workspace is loaded by `mr_lang.workspace.loader` and assembled into a system prompt
- Keep SOUL.md focused — overly long personality rules degrade agent performance
- USER.md can be updated dynamically by the agent (long-term memory)
