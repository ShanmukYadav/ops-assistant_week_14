import os
import csv
import glob
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")

DATA_DIR   = Path(os.getenv("DATA_DIR",   "./data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("ops-assistant")


# ── Input schemas ────────────────────────────────────────────────────────────

class SearchInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=200,
                       description="Keyword or phrase to search for in documents")

    @field_validator("query")
    @classmethod
    def no_path_traversal(cls, v):
        if any(c in v for c in ["/", "\\", "..", "<", ">"]):
            raise ValueError("Query contains invalid characters")
        return v.strip()


class RecordInput(BaseModel):
    order_id: str = Field(..., min_length=3, max_length=20,
                          description="Order ID to look up, e.g. ORD-1042")

    @field_validator("order_id")
    @classmethod
    def validate_format(cls, v):
        v = v.strip().upper()
        if not v.startswith("ORD-"):
            raise ValueError("order_id must start with 'ORD-', e.g. ORD-1042")
        if not v[4:].isdigit():
            raise ValueError("order_id must be in format ORD-<number>, e.g. ORD-1042")
        return v


class ReportInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=100,
                       description="Report title, used as the filename")
    content: str = Field(..., min_length=10, max_length=10000,
                         description="Full markdown content of the report")

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v):
        v = v.strip()
        for c in ["/", "\\", "..", "<", ">", ":", "|", "?", "*"]:
            if c in v:
                raise ValueError(f"Title contains invalid character: {c}")
        return v


# ── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_documents(query: str) -> str:
    """
    Search all .txt documents in the data folder for a keyword or phrase.
    Returns matching document IDs, titles, and the lines that matched.
    If nothing is found, says so clearly — never fabricates results.
    """
    try:
        params = SearchInput(query=query)
    except Exception as e:
        return f"[ERROR] Invalid input: {e}"

    keyword = params.query.lower()
    results = []

    txt_files = sorted(glob.glob(str(DATA_DIR / "*.txt")))
    if not txt_files:
        return "[ERROR] No documents found in data directory."

    for filepath in txt_files:
        doc_name = Path(filepath).name
        try:
            text = Path(filepath).read_text(encoding="utf-8")
        except Exception as e:
            results.append(f"[WARN] Could not read {doc_name}: {e}")
            continue

        lines = text.splitlines()
        matched_lines = [
            f"  Line {i+1}: {line.strip()}"
            for i, line in enumerate(lines)
            if keyword in line.lower()
        ]

        if matched_lines:
            # Pull title from first line if it starts with "Title:"
            title_line = lines[0].strip() if lines else doc_name
            results.append(
                f"Document: {doc_name}\n{title_line}\n" + "\n".join(matched_lines)
            )

    if not results:
        return f"[NO RESULTS] No documents matched the query: '{params.query}'"

    header = f"Search results for '{params.query}' — {len(results)} document(s) matched:\n"
    return header + "\n\n".join(results)


@mcp.tool()
def read_record(order_id: str) -> str:
    """
    Look up a single order record by order ID from orders.csv.
    Returns all fields for that order, clearly labelled.
    If the order is not found, says so — never fabricates a record.
    """
    try:
        params = RecordInput(order_id=order_id)
    except Exception as e:
        return f"[ERROR] Invalid input: {e}"

    csv_path = DATA_DIR / "orders.csv"
    if not csv_path.exists():
        return "[ERROR] orders.csv not found in data directory."

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("order_id", "").strip().upper() == params.order_id:
                    lines = [f"Record found — source: orders.csv"]
                    for k, v in row.items():
                        lines.append(f"  {k}: {v}")
                    return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] Could not read orders.csv: {e}"

    return f"[NO RESULTS] No record found for order ID: {params.order_id}"


@mcp.tool()
def save_report(title: str, content: str) -> str:
    """
    Save a markdown report to the outputs folder.
    The title becomes the filename. Content must be the full report text.
    Returns the path where the file was saved.
    """
    try:
        params = ReportInput(title=title, content=content)
    except Exception as e:
        return f"[ERROR] Invalid input: {e}"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = params.title.replace(" ", "_").lower()
    filename = f"{timestamp}_{safe_title}.md"
    output_path = OUTPUT_DIR / filename

    try:
        output_path.write_text(params.content, encoding="utf-8")
    except Exception as e:
        return f"[ERROR] Could not write report: {e}"

    return f"[SAVED] Report written to: {output_path}"


# ── Resource: document index ─────────────────────────────────────────────────

@mcp.resource("docs://index")
def list_documents() -> str:
    """Lists all available documents in the data folder."""
    txt_files = sorted(glob.glob(str(DATA_DIR / "*.txt")))
    if not txt_files:
        return "No documents found."

    lines = ["Available documents:\n"]
    for filepath in txt_files:
        name = Path(filepath).name
        try:
            first_line = Path(filepath).read_text(encoding="utf-8").splitlines()[0]
        except Exception:
            first_line = "(unreadable)"
        lines.append(f"  {name} — {first_line}")

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Ops Assistant MCP server...")
    print(f"Data directory : {DATA_DIR.resolve()}")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")
    mcp.run(transport="stdio")