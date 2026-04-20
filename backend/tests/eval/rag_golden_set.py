"""
rag_golden_set.py — Ground-truth Q&A pairs derived from the 5 test documents.

Every answer here was hand-verified against the source document text.
The `expected_contains` list gives keyword fragments that MUST appear in
the model's answer for it to be considered correct.  All matching is
case-insensitive.

Used by:
  - test_rag_accuracy.py  (RAGAS-based eval, requires live server + pgvector)
  - quality_check.py      (standalone CLI report)
"""

from __future__ import annotations
from pathlib import Path

TEST_DOCS_DIR = Path(__file__).resolve().parents[3] / "test-documents"


# ── Document 01: RFP Digital Transformation (Meridian Housing) ────────────────

RFP_QUESTIONS = [
    {
        "id": "rfp_01",
        "document": "01_RFP_Digital_Transformation.txt",
        "question": "What is the total approved budget for this programme?",
        "expected_contains": ["2.8", "million", "£"],
        "ground_truth": "MHA has an approved budget envelope of £2.8M over three years for the full programme.",
    },
    {
        "id": "rfp_02",
        "document": "01_RFP_Digital_Transformation.txt",
        "question": "How many properties does Meridian Housing Association manage?",
        "expected_contains": ["14,200", "14200"],
        "ground_truth": "Meridian Housing Association manages a portfolio of 14,200 properties.",
    },
    {
        "id": "rfp_03",
        "document": "01_RFP_Digital_Transformation.txt",
        "question": "What is the deadline for submitting proposals?",
        "expected_contains": ["14 May", "May 2026", "17:00"],
        "ground_truth": "Proposals must be submitted by 17:00 on 14 May 2026.",
    },
    {
        "id": "rfp_04",
        "document": "01_RFP_Digital_Transformation.txt",
        "question": "What percentage of the evaluation is allocated to technical solution and approach?",
        "expected_contains": ["35%", "35"],
        "ground_truth": "Technical Solution and Approach is weighted at 35%.",
    },
    {
        "id": "rfp_05",
        "document": "01_RFP_Digital_Transformation.txt",
        "question": "What accessibility standard must the resident portal comply with?",
        "expected_contains": ["WCAG 2.1", "AA"],
        "ground_truth": "The portal must comply with WCAG 2.1 AA standard.",
    },
]


# ── Document 02: Project Brief — Castleford Financial Services ────────────────

BRIEF_QUESTIONS = [
    {
        "id": "brief_01",
        "document": "02_Project_Brief_Data_Platform.txt",
        "question": "What is the total assets under management at Castleford Financial Services?",
        "expected_contains": ["4.2 billion", "£4.2", "AUM"],
        "ground_truth": "Castleford Financial Services manages approximately £4.2 billion of assets under management.",
    },
    {
        "id": "brief_02",
        "document": "02_Project_Brief_Data_Platform.txt",
        "question": "How long is the engagement duration?",
        "expected_contains": ["12 weeks"],
        "ground_truth": "The total engagement duration is 12 weeks.",
    },
    {
        "id": "brief_03",
        "document": "02_Project_Brief_Data_Platform.txt",
        "question": "What are the out-of-scope items for this engagement?",
        "expected_contains": ["implementation", "data migration", "integration build"],
        "ground_truth": "Out of scope: implementation, data migration, integration build, and staff training.",
    },
    {
        "id": "brief_04",
        "document": "02_Project_Brief_Data_Platform.txt",
        "question": "What is the target for reducing the regulatory reporting cycle?",
        "expected_contains": ["12 days", "4 days"],
        "ground_truth": "The objective is to reduce the quarterly compliance cycle from 12 days to under 4 days.",
    },
]


# ── Documents 03/04: SOW Comparison (Northgate Council) ──────────────────────

SOW_QUESTIONS = [
    {
        "id": "sow_01",
        "document": "03_SOW_v1_Original.txt",
        "question": "What is the total fixed fee for this engagement?",
        "expected_contains": ["185,000", "£185"],
        "ground_truth": "The total fixed fee is £185,000 (excluding VAT).",
    },
    {
        "id": "sow_02",
        "document": "03_SOW_v1_Original.txt",
        "question": "What is the engagement duration and start date?",
        "expected_contains": ["12 weeks", "9 March", "March 2026"],
        "ground_truth": "The engagement runs for 12 weeks, starting 9 March 2026.",
    },
    {
        "id": "sow_03",
        "document": "03_SOW_v1_Original.txt",
        "question": "What is the governance structure for this engagement?",
        "expected_contains": ["Steering Group", "fortnightly", "weekly"],
        "ground_truth": "Programme Steering Group meets fortnightly; weekly status calls between BSBI Lead and Council Change Lead.",
    },
]


# ── Document 05: Programme Assurance Review (Highfield NHS Trust) ─────────────
# This is the richest document — most Q&A pairs are drawn from here.

PROGRAMME_QUESTIONS = [
    {
        "id": "prog_01",
        "document": "05_Programme_Document_Rich.txt",
        "question": "What is the total approved budget for the Digital Patient Records programme?",
        "expected_contains": ["6.4 million", "£6.4"],
        "ground_truth": "The approved budget is £6.4 million.",
    },
    {
        "id": "prog_02",
        "document": "05_Programme_Document_Rich.txt",
        "question": "How much has been spent to date and what is the current overspend?",
        "expected_contains": ["2.9", "500k", "overspend"],
        "ground_truth": "Spend to date is £2.9M against a planned £2.4M, representing a £500k overspend.",
    },
    {
        "id": "prog_03",
        "document": "05_Programme_Document_Rich.txt",
        "question": "How many risks are rated Critical and how many are rated High?",
        "expected_contains": ["4", "critical", "6", "high"],
        "ground_truth": "4 risks are rated Critical (Red) and 6 are rated High (Amber).",
    },
    {
        "id": "prog_04",
        "document": "05_Programme_Document_Rich.txt",
        "question": "Who is the most concerned stakeholder and why?",
        "expected_contains": ["Mark Thornton", "Chief Finance Officer", "budget"],
        "ground_truth": "Mark Thornton (CFO) is the most concerned stakeholder due to the budget trajectory.",
    },
    {
        "id": "prog_05",
        "document": "05_Programme_Document_Rich.txt",
        "question": "What decisions need to be made before 30 April 2026?",
        "expected_contains": ["budget", "revised", "board", "April"],
        "ground_truth": "DECISION-001: Board must approve revised budget up to £7.5M and deferred schedule by 30 April 2026.",
    },
    {
        "id": "prog_06",
        "document": "05_Programme_Document_Rich.txt",
        "question": "What is the deadline for appointing a Test Manager?",
        "expected_contains": ["14 April", "Test Manager"],
        "ground_truth": "DECISION-003: Board must approve Test Manager appointment by 14 April 2026.",
    },
    {
        "id": "prog_07",
        "document": "05_Programme_Document_Rich.txt",
        "question": "What are the critical risks in the programme?",
        "expected_contains": ["pharmacy", "JAC", "clinical engagement", "budget", "UAT"],
        "ground_truth": "Four critical risks: pharmacy integration (JAC), clinical engagement, budget overrun, and missing Test Manager for UAT.",
    },
    {
        "id": "prog_08",
        "document": "05_Programme_Document_Rich.txt",
        "question": "What percentage of nursing staff have attended training or engagement sessions?",
        "expected_contains": ["34%", "34"],
        "ground_truth": "Only 34% of nursing staff who will use the system have attended any training or engagement session.",
    },
    {
        "id": "prog_09",
        "document": "05_Programme_Document_Rich.txt",
        "question": "What is the change control rule for budget changes above £25,000?",
        "expected_contains": ["25,000", "Board approval", "Change Request"],
        "ground_truth": "Changes over £25,000 or 2 weeks' schedule impact require Board approval via a formal Change Request.",
    },
    {
        "id": "prog_10",
        "document": "05_Programme_Document_Rich.txt",
        "question": "What is the projected total budget overrun?",
        "expected_contains": ["820k", "1.1M", "820"],
        "ground_truth": "Budget is estimated to exceed the £6.4M envelope by £820k–£1.1M.",
    },
]


# ── Combined set for full eval runs ──────────────────────────────────────────

ALL_QUESTIONS = (
    RFP_QUESTIONS
    + BRIEF_QUESTIONS
    + SOW_QUESTIONS
    + PROGRAMME_QUESTIONS
)


def load_document_text(filename: str) -> str:
    """Load the full text of a test document."""
    return (TEST_DOCS_DIR / filename).read_text(encoding="utf-8")


def check_answer(answer: str, expected_contains: list[str]) -> tuple[bool, list[str]]:
    """
    Check whether `answer` contains all expected fragments (case-insensitive).
    Returns (passed: bool, missing: list[str]).
    """
    answer_lower = answer.lower()
    missing = [
        fragment for fragment in expected_contains
        if fragment.lower() not in answer_lower
    ]
    return (len(missing) == 0, missing)