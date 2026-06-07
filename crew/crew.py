import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import MCPServerAdapter
import litellm
from mcp import StdioServerParameters

load_dotenv()

# ── OpenRouter Configuration ────────────────────────────────────────────────

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
if not OPENROUTER_API_KEY:
    raise EnvironmentError("OPENROUTER_API_KEY is missing. Add it to your .env file.")

os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY

TRACES_DIR = Path(os.getenv("TRACES_DIR", "./traces"))
TRACES_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging / trace setup ────────────────────────────────────────────────────

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
trace_file = TRACES_DIR / f"trace_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(trace_file),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── LLM config ───────────────────────────────────────────────────────────────

litellm.cache = None
litellm.set_verbose = False

llm = LLM(
    model="openrouter/meta-llama/llama-3.1-8b-instruct",
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0.1,
)

# ── MCP server parameters ────────────────────────────────────────────────────

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(__file__).parent.parent / "server" / "server.py")],
    env=None,
)

# ── Run the crew ─────────────────────────────────────────────────────────────


def run_crew(question: str) -> str:
    log.info("=" * 60)
    log.info(f"Question: {question}")
    log.info("=" * 60)

    with MCPServerAdapter(server_params) as mcp_tools:
        log.info(f"Tools available from MCP server: {[t.name for t in mcp_tools]}")

        # ── Agents ───────────────────────────────────────────────────────────

        researcher = Agent(
            role="Operations Researcher",
            goal=(
                "Find accurate, grounded answers to business questions by searching "
                "documents and looking up order records. Every fact you report must "
                "name the exact document or record it came from. If a tool returns "
                "no results, say so — never invent an answer."
            ),
            backstory=(
                "You are a meticulous operations analyst. You only state facts you "
                "can point to in a document or a record. You call search_documents "
                "to find relevant policies or tickets, and read_record to pull up "
                "specific orders. You always note the source alongside every fact."
            ),
            tools=mcp_tools,
            llm=llm,
            verbose=True,
            max_iter=5,
            allow_delegation=False,
        )

        writer = Agent(
            role="Operations Report Writer",
            goal=(
                "Turn the researcher's findings into a clear, short markdown report. "
                "Every claim in the report must cite its source (document ID or order ID). "
                "If a claim has no source, remove it. Save the final report using save_report."
            ),
            backstory=(
                "You are a concise technical writer. You never add information the "
                "researcher did not provide. You structure the report with a summary, "
                "findings with inline citations, and a sources section at the end."
            ),
            tools=mcp_tools,
            llm=llm,
            verbose=True,
            max_iter=3,
            allow_delegation=False,
        )

        # ── Tasks ─────────────────────────────────────────────────────────────

        research_task = Task(
            description=(
                f"Answer the following business question using only the available tools:\n\n"
                f"QUESTION: {question}\n\n"
                f"Steps:\n"
                f"1. If an order ID is mentioned, call read_record first to get the order details.\n"
                f"2. Then call search_documents using the PRODUCT NAME from the order record as the query.\n"
                f"3. Also call search_documents with the order ID as the query (e.g. '1042').\n"
                f"4. Also call search_documents with 'inventory' to check stock levels.\n"
                f"5. Compile your findings. For every fact, write the source next to it "
                f"   in brackets, e.g. [doc_05] or [ORD-1042].\n"
                f"5. If no evidence is found after all searches, state that clearly — do not guess."
            ),
            expected_output=(
                "A structured list of findings where every fact is followed by its "
                "source in brackets. If no evidence was found, a clear statement saying so."
            ),
            agent=researcher,
        )

        write_task = Task(
            description=(
                f"Using ONLY the researcher's findings, write a short markdown report "
                f"that answers the question: '{question}'\n\n"
                f"Format:\n"
                f"# <title>\n\n"
                f"## Summary\n"
                f"One or two sentence answer.\n\n"
                f"## Findings\n"
                f"Bullet points. Each bullet cites its source, e.g. [doc_03] or [ORD-1042].\n\n"
                f"## Sources\n"
                f"List every document and record referenced.\n\n"
                f"Then call save_report with the title and the full report content."
            ),
            expected_output=(
                "A confirmation that save_report was called successfully, plus the "
                "full markdown report text."
            ),
            agent=writer,
            context=[research_task],
        )

        # ── Crew ──────────────────────────────────────────────────────────────

        crew = Crew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            process=Process.sequential,
            verbose=True,
        )

        log.info("Crew starting...")
        result = crew.kickoff()
        log.info("Crew finished.")
        log.info(f"Final output:\n{result}")
        log.info(f"Trace saved to: {trace_file}")

        return str(result)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    question = (
        "What was the issue with order ORD-1042, how was it resolved, "
        "and is the product still in stock?"
    )

    answer = run_crew(question)

    print("\n" + "=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(answer)
