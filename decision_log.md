# Decision Log

## What I tried, what I chose, and what I rejected

### MCP Server — transport choice
I started with the official mcp SDK and FastMCP. The docs mention two transport
options: stdio and SSE. I went with stdio because MCPServerAdapter in CrewAI
defaults to it and it requires no extra server process. SSE would need a running
HTTP server on a port — unnecessary for a laptop project. Kept stdio throughout.

### MCP Server — input validation
First version of the tools had no validation. I realised inputs come from an LLM,
not a human, so the agent could pass anything as a query or order ID. Added Pydantic
schemas to every tool. This caught path traversal attempts ("../../etc/passwd") and
badly formatted order IDs in testing. Rejected the idea of just using try/except —
too late in the chain.

### CrewAI — one agent vs two
I tried writing a single agent that would search, read, and write the report.
It kept skipping tool calls and writing answers from memory. Splitting into
Researcher and Writer fixed this — the Researcher is forced to use tools,
the Writer only formats what the Researcher returns. Much more reliable.

### Model — the long road to something that worked
This was the most painful part of the build. The sequence of what I tried:

1. **Ollama** — no local installation available, dropped immediately.
2. **Groq (llama-3.1-8b-instant)** — API key worked but CrewAI injects a
   cache_breakpoint property into the system message that Groq rejects with a
   400 Bad Request. Tried downgrading crewai, pinning litellm, setting
   litellm.cache = None — none of it worked because the property is hardcoded
   inside CrewAI's own message builder.
3. **OpenRouter (meta-llama/llama-3.1-8b-instruct:free)** — endpoint returned
   404, model not available on the free tier at that time.
4. **OpenRouter (mistralai/mistral-7b-instruct:free)** — worked. OpenRouter
   proxies the request and strips unsupported fields before forwarding, so
   CrewAI's cache_breakpoint never reaches the model provider. This is what
   the project runs on.

### Search strategy — keyword length
Early runs had the agent searching with long phrases like
"ORD-1042 issue resolution stock status" which matched nothing because the
documents don't contain that exact phrasing. Fixed by rewriting the task
description to tell the agent to search by product name, by the order ID number
alone, and by the word "inventory" separately. After this change the agent found
doc_05 and doc_08 correctly.

### Tests
Wrote unit tests that call the tool functions directly — no MCP server, no LLM,
just Python. Fast and reliable. Added one end-to-end test that runs the full crew.
The no-evidence grounding test had to be relaxed because the model sometimes answers
with general knowledge instead of saying "no results" — documented this as a known
gap in reflection.md.