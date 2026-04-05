---
name: web-research
description: Research a topic by fetching and summarizing web content
emoji: "\U0001F50D"
requires:
  tools: [http_request]
  env: []
tags: [research, web]
---

# Web Research

## When to Use
When the user asks you to research a topic, find information online, or summarize content from a URL.

## Workflow

### Step 1: Understand the Query
Parse what the user wants to know. Identify key search terms.

### Step 2: Fetch Content
Use the `http_request` tool to fetch relevant web pages.

### Step 3: Extract and Summarize
Read the fetched content, extract relevant information, and present a clear summary.

## Important Rules
- Always cite the source URL
- Summarize rather than dump raw content
- If a page fails to load, try an alternative source
- Present findings in a structured format with headers
