"""Tests for the Excel/CSV parser."""
from __future__ import annotations

import io
import pytest


def _make_generic_excel(rows: list[dict]) -> bytes:
    """Create a minimal generic Excel file with headers."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_csv(rows: list[dict]) -> bytes:
    import csv
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


class TestGenericExcelParser:
    def test_detects_id_and_narrative_columns(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring

        data = [
            {"project_id": "PROJ-001", "narrative": "This is a test narrative with enough content."},
            {"project_id": "PROJ-002", "narrative": "Another narrative for testing purposes here."},
        ]
        raw = _make_generic_excel(data)
        records = parse_excel_for_scoring(raw, filename="test.xlsx")
        assert len(records) == 2
        assert records[0]["unique_id"] == "PROJ-001"
        assert "test narrative" in records[0]["narrative_text"]

    def test_detects_text_column(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring

        data = [{"reference": "REF-A", "text": "Some narrative content here."}]
        raw = _make_generic_excel(data)
        records = parse_excel_for_scoring(raw, filename="test.xlsx")
        assert records[0]["unique_id"] == "REF-A"
        assert records[0]["narrative_text"] == "Some narrative content here."

    def test_extra_fields_preserved(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring

        data = [{"id": "X1", "narrative": "Some text.", "department": "Finance", "period": "Q1"}]
        raw = _make_generic_excel(data)
        records = parse_excel_for_scoring(raw, filename="test.xlsx")
        assert records[0]["extra_fields"]["department"] == "Finance"
        assert records[0]["extra_fields"]["period"] == "Q1"

    def test_skips_rows_with_no_id(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring

        data = [
            {"id": "VALID", "narrative": "Some narrative."},
            {"id": "", "narrative": "No ID row."},
        ]
        raw = _make_generic_excel(data)
        records = parse_excel_for_scoring(raw, filename="test.xlsx")
        assert len(records) == 1
        assert records[0]["unique_id"] == "VALID"

    def test_raises_on_missing_columns(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring

        data = [{"column_a": "value", "column_b": "other"}]
        raw = _make_generic_excel(data)
        with pytest.raises((ValueError, Exception)):
            parse_excel_for_scoring(raw, filename="test.xlsx")

    def test_alternative_column_names(self) -> None:
        from backend.app.services.excel_parser import parse_excel_for_scoring

        data = [{"unique_id": "U001", "description": "Description text for testing."}]
        raw = _make_generic_excel(data)
        records = parse_excel_for_scoring(raw)
        assert records[0]["unique_id"] == "U001"
        assert records[0]["narrative_text"] == "Description text for testing."


class TestCSVParser:
    def test_basic_csv_parsing(self) -> None:
        from backend.app.services.excel_parser import parse_csv_for_scoring

        data = [{"project": "P001", "narrative": "CSV narrative content here."}]
        raw = _make_csv(data)
        records = parse_csv_for_scoring(raw)
        assert len(records) == 1
        assert records[0]["unique_id"] == "P001"

    def test_csv_with_body_column(self) -> None:
        from backend.app.services.excel_parser import parse_csv_for_scoring

        data = [{"ref": "R1", "body": "Body text of narrative."}]
        raw = _make_csv(data)
        records = parse_csv_for_scoring(raw)
        assert records[0]["narrative_text"] == "Body text of narrative."

    def test_csv_missing_columns_raises(self) -> None:
        from backend.app.services.excel_parser import parse_csv_for_scoring

        data = [{"column_x": "abc", "column_y": "xyz"}]
        raw = _make_csv(data)
        with pytest.raises(ValueError, match="unique ID"):
            parse_csv_for_scoring(raw)


class TestContentBuilder:
    def test_build_content_string(self) -> None:
        from backend.app.services.excel_parser import build_content_string

        record = {
            "unique_id": "PROJ-01",
            "narrative_text": "Test narrative text.",
            "extra_fields": {"period": "Q1", "department": "Finance"},
        }
        content = build_content_string(record)
        assert "PROJ-01" in content
        assert "Test narrative text." in content
        assert "Q1" in content
        assert "Finance" in content

    def test_build_content_string_no_extras(self) -> None:
        from backend.app.services.excel_parser import build_content_string

        record = {"unique_id": "X", "narrative_text": "Narrative.", "extra_fields": {}}
        content = build_content_string(record)
        assert "X" in content
        assert "Narrative." in content