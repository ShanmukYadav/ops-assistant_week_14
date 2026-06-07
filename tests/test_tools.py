import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.server import search_documents, read_record, save_report

# ── search_documents ─────────────────────────────────────────

def test_search_finds_known_keyword():
    result = search_documents("firmware")
    assert "[NO RESULTS]" not in result
    assert "doc_03" in result or "doc_05" in result

def test_search_finds_ticket_by_order_id():
    result = search_documents("1042")
    assert "doc_05" in result
    assert "Support Ticket" in result

def test_search_finds_inventory():
    result = search_documents("inventory")
    assert "doc_08" in result

def test_search_no_results():
    result = search_documents("xyznonexistent999")
    assert "[NO RESULTS]" in result

def test_search_rejects_path_traversal():
    result = search_documents("../../etc/passwd")
    assert "[ERROR]" in result

def test_search_rejects_empty():
    result = search_documents("")
    assert "[ERROR]" in result

# ── read_record ──────────────────────────────────────────────

def test_read_record_found():
    result = read_record("ORD-1042")
    assert "Priya Sharma" in result
    assert "ProSound X200" in result
    assert "returned" in result

def test_read_record_case_insensitive():
    result = read_record("ord-1042")
    assert "Priya Sharma" in result

def test_read_record_not_found():
    result = read_record("ORD-9999")
    assert "[NO RESULTS]" in result

def test_read_record_bad_format():
    result = read_record("12345")
    assert "[ERROR]" in result

def test_read_record_another_order():
    result = read_record("ORD-1087")
    assert "Arjun Mehta" in result
    assert "MechType K80" in result

# ── save_report ──────────────────────────────────────────────

def test_save_report_creates_file(tmp_path, monkeypatch):
    import server.server as srv
    monkeypatch.setattr(srv, "OUTPUT_DIR", tmp_path)
    result = save_report("Test Report", "# Test\n\nThis is a test report.")
    assert "[SAVED]" in result
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    assert "test report" in files[0].read_text().lower() or "test" in files[0].name

def test_save_report_rejects_path_traversal():
    result = save_report("../evil", "content")
    assert "[ERROR]" in result

def test_save_report_rejects_short_content():
    result = save_report("Valid Title", "short")
    assert "[ERROR]" in result