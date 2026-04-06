---
name: add-skill
description: Scaffold a new SKILL.md file with correct YAML frontmatter for agent skill definitions
---

# Add Skill

Create a new skill definition for the mr_lang framework. Skills are Markdown files with YAML frontmatter that get injected into the agent's system prompt when activated.

## Instructions

When the user asks to add a new skill, follow these steps:

1. Ask for the skill name (kebab-case) and purpose if not provided
2. Create the skill file at the appropriate location:
   - For a plugin: `src/<module>/skills/<name>.SKILL.md`
   - For an example: `examples/skills/<name>.SKILL.md`

## Skill Template

```markdown
---
name: <skill-name>
description: <One-line description of what this skill does>
emoji: "<relevant emoji>"
requires:
  env: []          # Required environment variables, e.g. [API_KEY, SECRET]
  tools: []        # Required tool names, e.g. [search_knowledge, read_file]
  config: []       # Required config keys
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

## How Skills Work at Runtime

1. Plugin loader discovers `*.SKILL.md` files from the plugin's `skills_dir`
2. Skills are loaded into the `SkillRegistry`
3. In `setup_agent()`, each skill's requirements are validated against the `ToolRegistry`
4. Valid skills are appended to the system prompt via `skill_to_prompt_section()`
5. In Telegram, skills are registered as `/` commands via `set_my_commands()`

## Rules

- Skill name MUST be kebab-case (e.g., `web-research`, `code-review`)
- File MUST end with `.SKILL.md` extension
- Skills are NOT tools — they are prompt injections (instructions for the agent)
- The `requires` section declares dependencies validated at load time:
  - `env`: Environment variables that must be set
  - `tools`: Tool names that must be registered in the ToolRegistry
- Skills with unmet requirements are skipped with a warning (warn-not-crash pattern)
- Keep instructions clear and actionable — the agent follows them literally
- Use numbered steps for sequential workflows
- Reference specific tools by name if the skill depends on them
- In Telegram, the `description` and `emoji` fields appear in the `/` command menu
