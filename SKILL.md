---
name: mcp-server-graphiti
description: "Store and search temporal AI-agent memory in a Graphiti knowledge graph."
---

# Graphiti MCP Server

Use this server when an agent needs persistent, temporal memory that can be
searched by semantic entities and facts. Search for existing knowledge before
adding information. Use `group_id` consistently to isolate independent memory
domains. `Preference`, `Requirement`, and `Procedure` entity types are preferred
when they match the content.

The packaged companion starts in read-only mode. Enable write tools deliberately
only for trusted clients and keep `OPENAI_API_KEY` and database credentials in
the environment, never in tool arguments.
