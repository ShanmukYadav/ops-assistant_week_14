# Reflection

## Why these tools and these agent roles?

The three tools map to exactly what an ops staff member does by hand: open a
document and search it, pull up a specific order, write a summary. search_documents
covers the document folder, read_record covers the CSV, and save_report closes the
loop by writing the output to disk. I considered a fourth tool to list all documents
but used a resource endpoint (docs://index) instead since listing is read-only and
does not need to be an agent-callable tool.

Two agents made more sense than one. When I tried a single agent it kept skipping
tool calls and writing answers from its own training data. Splitting into Researcher
and Writer enforced a clear contract: the Researcher must use tools and cite sources,
the Writer can only use what the Researcher returned. That separation is what makes
the answers trustworthy.

## What broke first when connecting the crew to the server?

Three things broke, one after another.

First, the server path. I was running crew.py from inside the crew/ folder, so
"server/server.py" resolved to nothing. Fixed by using sys.executable and building
an absolute path with Path(__file__).parent.parent.

Second, the model. Groq was the first choice because it is fast and free. It
connected fine but rejected every single request with a 400 error —
"cache_breakpoint is unsupported". This property is injected by CrewAI into the
system message and there is no config option to turn it off. I tried downgrading
crewai, pinning litellm to an older version, and setting litellm.cache = None.
None of it worked. Switched to OpenRouter which proxies the request and strips
unsupported fields before forwarding — problem gone immediately.

Third, the search queries. The agent was constructing long exact-match phrases
that returned no results. Rewrote the task description to instruct the agent to
search with short targeted keywords. After that it found the right documents.

## One answer the crew got wrong or ungrounded

When asked about the AirPods Pro warranty — a product that does not exist in
the data — the model sometimes produced a generic answer using its own training
knowledge instead of saying "no evidence found." The guardrail check looks for
phrases like "no results" or "not found" in the output, but the model phrased
its uncertainty differently each time, so the check did not always catch it.
This slipped through because the model has general knowledge about Apple products
and used it as a fallback. A proper fix would be a second checker agent that
verifies every claim in the report against the actual tool outputs and flags
anything that does not have a source citation.

## Biggest security risk and how it was reduced

The biggest risk is path traversal. If the LLM passes "../../etc/passwd" as a
search query or "ORD-../config" as an order ID, a naive tool would try to open
that path. I added Pydantic validators on every tool input — the query validator
rejects strings containing "/", "\", or "..", and the order ID validator enforces
the strict "ORD-<digits>" format. The unit tests verify both cases explicitly.

The second risk is that the MCP server runs as a subprocess on the local machine
with access to the file system. Right now it can only read from ./data and write
to ./outputs, but there is nothing stopping a compromised tool call from doing
more if the validation were weaker.

## What would you change before letting this touch real company data?

Honestly quite a lot.

The keyword search would need to become a vector search. Right now if a document
says "firmware dropout" and the agent searches for "audio issue" it finds nothing.
Embeddings would fix that.

The save_report tool writes to disk immediately with no approval step. I would add
a human-in-the-loop gate before anything gets written — the agent proposes the
report, a human approves it, then it saves.

The MCP server would run inside a Docker container with read-only mounts on the
data folder and a strict write path for outputs. No access to the rest of the
file system.

The API key is currently in a .env file on the developer machine. For real use
that should go into a secrets manager like AWS Secrets Manager or Azure Key Vault,
rotated automatically.

And the model would need to be evaluated properly on a set of known questions with
known answers before going anywhere near real customer data. The grounding is
good enough for a demo but not for production.