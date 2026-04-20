"""
test_rag_accuracy.py — Evaluation tests for RAG retrieval and chat accuracy.

These tests call the LIVE running server (http://localhost:8000) — they are
NOT part of the standard pytest run.  Run them explicitly:

    pytest backend/tests/eval/ -m eval -v

Requirements:
  - Backend server running: uvicorn backend.app.main:app --port 8000
  - At least one LLM provider configured (OPENAI_API_KEY or similar)
  - The 5 test documents must be in test-documents/

What is measured:
  1. RAG recall   — does the answer contain the expected ground-truth fragments?
  2. Hallucination guard — does the model add figures NOT in the source?
  3. Generation quality — do generated SOW/Bid documents score ≥ threshold
     when validated against the default rubric?
"""

from __future__ import annotations

import os
import time
import pytest
import httpx

from backend.tests.eval.rag_golden_set import (
    ALL_QUESTIONS,
    PROGRAMME_QUESTIONS,
    RFP_QUESTIONS,
    load_document_text,
    check_answer,
)

BASE_URL   = os.getenv("EVAL_BASE_URL", "http://localhost:8000")
EVAL_EMAIL = "eval_tester@bsbi.test"
EVAL_PASS  = "EvalPass999!"
LLM_PROVIDER = os.getenv("EVAL_LLM_PROVIDER", "openai")
LLM_MODEL    = os.getenv("EVAL_LLM_MODEL", None)

# Minimum acceptable scores
MIN_RAG_RECALL      = float(os.getenv("MIN_RAG_RECALL", "0.75"))       # 75% questions answered correctly
MIN_QUALITY_SCORE   = float(os.getenv("MIN_QUALITY_SCORE", "65.0"))    # % compliance score from rubric

pytestmark = pytest.mark.eval


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def http():
    """Shared httpx client for all eval tests."""
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        yield client


@pytest.fixture(scope="module")
def eval_token(http):
    """Register/login an eval user and return a bearer token."""
    # Try register first; if it exists, fall back to login
    r = http.post("/api/v1/auth/register", json={"email": EVAL_EMAIL, "password": EVAL_PASS})
    if r.status_code == 200:
        return r.json()["access_token"]

    r = http.post("/api/v1/auth/login", json={"email": EVAL_EMAIL, "password": EVAL_PASS})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth(eval_token):
    return {"Authorization": f"Bearer {eval_token}"}


@pytest.fixture(scope="module")
def uploaded_docs(http, auth):
    """
    Upload all test documents to the platform and return a dict of
    {filename: parse_response}.  Uploads are skipped if the server is
    unreachable (marks the test as xfail).
    """
    from pathlib import Path
    TEST_DOCS = Path(__file__).resolve().parents[3] / "test-documents"

    docs = {}
    filenames = [
        "01_RFP_Digital_Transformation.txt",
        "02_Project_Brief_Data_Platform.txt",
        "03_SOW_v1_Original.txt",
        "05_Programme_Document_Rich.txt",
    ]
    for fname in filenames:
        fpath = TEST_DOCS / fname
        if not fpath.exists():
            continue
        with open(fpath, "rb") as f:
            resp = http.post(
                "/api/v1/parse",
                files={"file": (fname, f, "text/plain")},
                data={"llm_provider": LLM_PROVIDER},
                headers=auth,
            )
        assert resp.status_code == 200, f"Parse failed for {fname}: {resp.text}"
        docs[fname] = resp.json()
        time.sleep(0.5)  # avoid hammering the LLM provider

    return docs


# ── RAG accuracy tests ────────────────────────────────────────────────────────

class TestRAGAccuracy:
    """
    Upload each test document, ask a question about it, check the answer
    contains expected ground-truth fragments.
    """

    def _ask(self, http, auth, question: str, project_id: int | None = None) -> str:
        payload = {
            "question": question,
            "llm_provider": LLM_PROVIDER,
            "project_id": project_id,
        }
        if LLM_MODEL:
            payload["llm_model"] = LLM_MODEL
        resp = http.post("/api/v1/chat", json=payload, headers=auth)
        assert resp.status_code == 200, f"Chat failed: {resp.text}"
        return resp.json()["answer"]

    def test_rag_recall_programme_document(self, http, auth, uploaded_docs):
        """
        Ask all PROGRAMME_QUESTIONS (richest doc) and measure recall.
        We expect >= MIN_RAG_RECALL of questions to be answered correctly.
        """
        if "05_Programme_Document_Rich.txt" not in uploaded_docs:
            pytest.skip("Programme document not uploaded")

        parse_resp = uploaded_docs["05_Programme_Document_Rich.txt"]
        project_id = parse_resp.get("project_id")

        passed = 0
        failures = []

        for qa in PROGRAMME_QUESTIONS:
            answer = self._ask(http, auth, qa["question"], project_id)
            ok, missing = check_answer(answer, qa["expected_contains"])
            if ok:
                passed += 1
            else:
                failures.append({
                    "id": qa["id"],
                    "question": qa["question"],
                    "missing": missing,
                    "answer_snippet": answer[:200],
                })
            time.sleep(1)  # rate limiting

        recall = passed / len(PROGRAMME_QUESTIONS)
        print(f"\nRAG recall on Programme doc: {passed}/{len(PROGRAMME_QUESTIONS)} = {recall:.0%}")
        if failures:
            print("\nFailed questions:")
            for f in failures:
                print(f"  [{f['id']}] {f['question']}")
                print(f"  Missing: {f['missing']}")
                print(f"  Answer: {f['answer_snippet']}…\n")

        assert recall >= MIN_RAG_RECALL, (
            f"RAG recall {recall:.0%} below threshold {MIN_RAG_RECALL:.0%}. "
            f"Failed: {[f['id'] for f in failures]}"
        )

    def test_rag_recall_rfp_document(self, http, auth, uploaded_docs):
        """Ask RFP-specific questions — budget, timeline, evaluation criteria."""
        if "01_RFP_Digital_Transformation.txt" not in uploaded_docs:
            pytest.skip("RFP document not uploaded")

        parse_resp = uploaded_docs["01_RFP_Digital_Transformation.txt"]
        project_id = parse_resp.get("project_id")

        passed = 0
        for qa in RFP_QUESTIONS:
            answer = self._ask(http, auth, qa["question"], project_id)
            ok, _ = check_answer(answer, qa["expected_contains"])
            if ok:
                passed += 1
            time.sleep(1)

        recall = passed / len(RFP_QUESTIONS)
        print(f"\nRFP recall: {passed}/{len(RFP_QUESTIONS)} = {recall:.0%}")
        assert recall >= MIN_RAG_RECALL

    def test_hallucination_guard_budget_figure(self, http, auth, uploaded_docs):
        """
        Ask about the budget in the NHS programme document.
        The model should NOT hallucinate a figure that isn't in the source.
        """
        if "05_Programme_Document_Rich.txt" not in uploaded_docs:
            pytest.skip("Programme document not uploaded")

        parse_resp = uploaded_docs["05_Programme_Document_Rich.txt"]
        answer = self._ask(
            http, auth,
            "What is the approved total budget for the Highfield NHS programme?",
            parse_resp.get("project_id"),
        )

        # Should contain the correct figure
        assert "6.4" in answer or "6,400" in answer.replace(",", ""), (
            f"Expected '6.4' in answer, got: {answer[:300]}"
        )
        # Should NOT hallucinate wildly different figures
        bad_figures = ["10 million", "£10M", "£15", "£20", "£50"]
        for bad in bad_figures:
            assert bad.lower() not in answer.lower(), (
                f"Possible hallucination — '{bad}' found in answer: {answer[:300]}"
            )


# ── Generation quality tests ──────────────────────────────────────────────────

class TestGenerationQuality:
    """
    Generate a SOW and a Bid from known test documents, then validate each
    against the default rubric.  Compliance score must meet MIN_QUALITY_SCORE.
    """

    def _get_default_rubric_id(self, http, auth) -> int:
        resp = http.get("/api/v1/rubrics", headers=auth)
        assert resp.status_code == 200
        rubrics = resp.json()
        defaults = [r for r in rubrics if r["is_default"]]
        assert defaults, "No default rubric found — ensure server has run init_db()"
        return defaults[0]["id"]

    def test_sow_generation_quality(self, http, auth, uploaded_docs):
        """
        Generate a SOW from the Castleford Financial project brief and
        score it.  Compliance must be >= MIN_QUALITY_SCORE.
        """
        if "02_Project_Brief_Data_Platform.txt" not in uploaded_docs:
            pytest.skip("Project brief not uploaded")

        parse = uploaded_docs["02_Project_Brief_Data_Platform.txt"]
        doc = parse["document"]

        sow_payload = {
            "client_name": "Castleford Financial Services",
            "project_name": "Client Data & Analytics Platform",
            "source_document": {
                "title": doc["title"],
                "text": doc["text"],
                "sections": doc["sections"],
            },
            "assumptions": ["SMEs available 4 hrs/week", "Read access to documentation"],
            "project_id": parse.get("project_id"),
            "llm_provider": LLM_PROVIDER,
            **({"llm_model": LLM_MODEL} if LLM_MODEL else {}),
        }

        sow_resp = http.post("/api/v1/generate/sow", json=sow_payload, headers=auth)
        assert sow_resp.status_code == 200, f"SOW generation failed: {sow_resp.text}"
        sow_data = sow_resp.json()

        # Extract full text from sections to validate
        section_text = "\n\n".join(
            f"## {s['title']}\n" + "\n".join(s.get("paragraphs", []) + s.get("bullets", []))
            for s in sow_data.get("sections", [])
        )
        assert section_text.strip(), "SOW returned no section text"

        rubric_id = self._get_default_rubric_id(http, auth)
        val_resp = http.post(
            "/api/v1/validate",
            json={
                "text": section_text,
                "document_name": "Generated_SOW_Quality_Check",
                "rubric_id": rubric_id,
                "llm_provider": LLM_PROVIDER,
                **({"llm_model": LLM_MODEL} if LLM_MODEL else {}),
            },
            headers=auth,
        )
        assert val_resp.status_code == 200, f"Validation failed: {val_resp.text}"
        val = val_resp.json()
        score = val["layer1"]["compliance_score"]

        print(f"\nSOW quality score: {score:.1f}%  (verdict: {val['overall_verdict']})")
        print(f"Issues: {val['layer1'].get('issues', [])}")

        assert score >= MIN_QUALITY_SCORE, (
            f"SOW quality score {score:.1f}% below threshold {MIN_QUALITY_SCORE}%. "
            f"Issues: {val['layer1'].get('issues', [])}"
        )

    def test_bid_generation_quality(self, http, auth, uploaded_docs):
        """
        Generate a Bid Response from the Meridian Housing RFP and score it.
        """
        if "01_RFP_Digital_Transformation.txt" not in uploaded_docs:
            pytest.skip("RFP document not uploaded")

        parse = uploaded_docs["01_RFP_Digital_Transformation.txt"]
        doc = parse["document"]

        bid_payload = {
            "client_name": "Meridian Housing Association",
            "opportunity_title": "Digital Transformation Programme",
            "source_document": {
                "title": doc["title"],
                "text": doc["text"],
                "sections": doc["sections"],
            },
            "our_strengths": [
                "Proven housing sector delivery",
                "Dedicated UK team",
                "Fixed-price commercial model",
            ],
            "project_id": parse.get("project_id"),
            "llm_provider": LLM_PROVIDER,
            **({"llm_model": LLM_MODEL} if LLM_MODEL else {}),
        }

        bid_resp = http.post("/api/v1/generate/bid", json=bid_payload, headers=auth)
        assert bid_resp.status_code == 200, f"Bid generation failed: {bid_resp.text}"
        bid_data = bid_resp.json()

        section_text = "\n\n".join(
            f"## {s['title']}\n" + "\n".join(s.get("paragraphs", []) + s.get("bullets", []))
            for s in bid_data.get("sections", [])
        )
        assert section_text.strip(), "Bid returned no section text"

        rubric_id = self._get_default_rubric_id(http, auth)
        val_resp = http.post(
            "/api/v1/validate",
            json={
                "text": section_text,
                "document_name": "Generated_Bid_Quality_Check",
                "rubric_id": rubric_id,
                "llm_provider": LLM_PROVIDER,
                **({"llm_model": LLM_MODEL} if LLM_MODEL else {}),
            },
            headers=auth,
        )
        assert val_resp.status_code == 200
        val = val_resp.json()
        score = val["layer1"]["compliance_score"]

        print(f"\nBid quality score: {score:.1f}%  (verdict: {val['overall_verdict']})")
        assert score >= MIN_QUALITY_SCORE, (
            f"Bid quality score {score:.1f}% below threshold {MIN_QUALITY_SCORE}%."
        )


# ── Embedding sanity checks ───────────────────────────────────────────────────

class TestEmbeddingQuality:
    """
    Verify that the embedding layer is configured and can retrieve chunks
    relevant to a known query.  These are fast smoke tests, not deep evals.
    """

    def test_vector_store_configured(self, http):
        resp = http.get("/api/v1/vector/status")
        assert resp.status_code == 200
        status = resp.json()
        print(f"\nVector store status: {status}")
        # Just report — don't fail if not configured (pgvector is optional)
        if not status.get("configured"):
            pytest.skip("pgvector not configured — skipping embedding tests")

    def test_chunk_retrieval_returns_relevant_result(self, http, auth, uploaded_docs):
        """
        Ask a very specific question whose answer is a single sentence in the doc.
        Verify the chat response references the correct document content.
        """
        if "05_Programme_Document_Rich.txt" not in uploaded_docs:
            pytest.skip("Programme document not uploaded")

        parse_resp = uploaded_docs["05_Programme_Document_Rich.txt"]
        project_id = parse_resp.get("project_id")

        resp = http.post(
            "/api/v1/chat",
            json={
                "question": "What is the day rate range for the Test Manager role?",
                "llm_provider": LLM_PROVIDER,
                "project_id": project_id,
            },
            headers=auth,
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"]

        # The exact figure is in the doc: "£650–£750/day"
        ok, missing = check_answer(answer, ["650", "750"])
        print(f"\nChunk retrieval answer: {answer[:300]}")
        assert ok, f"Expected day rate figures in answer. Missing: {missing}"