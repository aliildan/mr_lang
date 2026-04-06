# Agents

## Model Selection

Memo is a lightweight assistant — it mostly reads/writes files and calls simple tools. A small-to-medium model is sufficient.

**Recommended:**
- `llama3.1:8b` (fast, good for quick capture)
- `qwen2.5:7b` (good multilingual support if you switch languages)
- `gpt-4o-mini` (OpenAI, fast and cheap)

**Set in `.env`:**
```
MR_LANG_DEFAULT_PROVIDER=ollama
MR_LANG_DEFAULT_MODEL=llama3.1:8b
```

## Recursion Limit

The daily briefing and weekly review skills make several tool calls in sequence. The default limit of 50 steps is sufficient.
