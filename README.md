# Operations Assistant — Week 14 Mini-Project

A multi-agent CrewAI crew that answers business questions over local documents and records,
using tools exposed by a local MCP server.

## Stack
- MCP server: FastMCP (official `mcp` SDK)
- Agents: CrewAI with MCPServerAdapter over stdio
- Model: Ollama (local, free) — default llama3.2

## Setup

### 1. Clone and enter the repo
git clone <your-repo-url>
cd ops-assistant

### 2. Install dependencies
pip install mcp crewai "crewai-tools[mcp]" python-dotenv pydantic

### 3. Pull the local model
ollama pull llama3.2

### 4. Copy env file
cp .env.example .env

### 5. Run the MCP server (standalone, for Inspector testing)
python server/server.py

### 6. Run the crew
python crew/crew.py

### 7. Run tests
python -m pytest tests/

## Folder structure
ops-assistant/
├── data/               # Sample documents (.txt) and records (.csv)
├── server/             # MCP server (server.py)
├── crew/               # CrewAI agents and tasks (crew.py)
├── tests/              # Unit + end-to-end tests
├── traces/             # Saved agent run traces
├── outputs/            # Reports written by save_report tool
├── demo/               # 5-minute demo clip or link
├── .env.example
├── decision_log.md
└── reflection.md

## Example questions
See tests/ for three saved example runs with outputs and tool call logs.

## Security notes
- No API keys committed — use .env (gitignored)
- Tool inputs validated with Pydantic schemas
- max_iter set on all agents to prevent runaway loops