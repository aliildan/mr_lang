---
name: add-skill
description: Scaffold a new SKILL.md file with correct YAML frontmatter for agent skill definitions
---

# Add Skill

Create a new skill definition for the mr_lang framework. Skills are Markdown files with YAML frontmatter that get injected into the agent's system prompt when activated.

## Instructions

When the user asks to add a new skill, follow these steps:

1. Ask for the skill name (kebab-case) and purpose if not provided
2. Create the skill file at `examples/skills/<name>.SKILL.md` (or a custom path if specified)

## Skill Template

```markdown
---
name: <skill-name>
description: <One-line description of what this skill does>
emoji: <relevant emoji>
requires:
  env: []          # Required environment variables, e.g. [API_KEY, SECRET]
  tools: []        # Required tool names, e.g. [web_search, read_file]
  config: []       # Required config keys, e.g. [providers.ollama.base_url]
tags: []           # Categorization tags, e.g. [research, coding, teaching]
---

# <Skill Name>

## When to Use
<Describe when the agent should activate this skill>

## Workflow

### Step 1: <First step>
<Instructions for the agent>

### Step 2: <Second step>
<Instructions for the agent>

## Important Rules
- <Rule 1>
- <Rule 2>

## Output Format
<Describe expected output format>
```

## Rules

- Skill name MUST be kebab-case (e.g., `web-research`, `code-review`)
- File MUST end with `.SKILL.md` extension
- Skills are NOT tools — they are prompt injections (instructions for the agent)
- The `requires` section declares dependencies validated at load time
- Keep instructions clear and actionable — the agent follows them literally
- Use numbered steps for sequential workflows
- Reference specific tools by name in the workflow if the skill depends on them
