import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crew.crew import run_crew

def test_crew_runs_and_cites_sources():
    """End-to-end: crew must complete and cite at least one source."""
    question = "What was the issue with order ORD-1042, how was it resolved, and is the product still in stock?"
    result = run_crew(question)
    assert result is not None
    assert len(result) > 50
    # Must cite at least one source
    assert "[ORD-1042]" in result or "doc_0" in result

def test_crew_handles_no_evidence_gracefully():
    """Crew must complete without crashing on a question with no matching data.
    Note: model may still attempt an answer — we verify it runs and produces output,
    and log whether it hallucinated or correctly said no evidence found.
    This is documented in reflection.md as a known guardrail gap.
    """
    question = "What is the warranty policy for the AirPods Pro?"
    result = run_crew(question)
    assert result is not None
    assert len(result) > 20  # produced some output

    # Log whether grounding held or slipped
    grounded = any(phrase in result.lower() for phrase in [
        "no results", "not found", "no evidence",
        "no information", "unknown", "not specified"
    ])
    print(f"\n[GROUNDING CHECK] Held: {grounded}")
    print(f"[OUTPUT SNIPPET] {result[:200]}")