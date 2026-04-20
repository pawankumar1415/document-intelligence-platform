"""
quality_check.py — Standalone CLI script for generation + RAG quality reporting.

Runs against the live backend server.  Produces a human-readable report with
scores for each test document and generation type.

Usage:
    python scripts/quality_check.py
    python scripts/quality_check.py --provider groq --model llama-3.3-70b-versatile
    python scripts/quality_check.py --rag-only
    python scripts/quality_check.py --gen-only

Environment variables (optional):
    EVAL_BASE_URL       default: http://localhost:8000
    EVAL_EMAIL          default: quality_check@bsbi.test
    EVAL_PASS           default: QualityCheck999!
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx

from backend.tests.eval.rag_golden_set import (
    ALL_QUESTIONS,
    PROGRAMME_QUESTIONS,
    RFP_QUESTIONS,
    BRIEF_QUESTIONS,
    SOW_QUESTIONS,
    check_answer,
    load_document_text,
)

BASE_URL   = os.getenv("EVAL_BASE_URL", "http://localhost:8000")
EMAIL      = os.getenv("EVAL_EMAIL",    "quality_check@bsbi.test")
PASSWORD   = os.getenv("EVAL_PASS",     "QualityCheck999!")
DOCS_DIR   = ROOT / "test-documents"


# ── ANSI colours ──────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def green(s):  return f"{GREEN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def red(s):    return f"{RED}{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_token(client: httpx.Client) -> str:
    r = client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        print(green("✓ Registered eval user"))
        return r.json()["access_token"]
    r = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        print(green("✓ Logged in as eval user"))
        return r.json()["access_token"]
    print(red(f"✗ Auth failed: {r.text}"))
    sys.exit(1)


# ── Document upload ───────────────────────────────────────────────────────────

def upload_documents(client: httpx.Client, auth: dict, provider: str) -> dict[str, dict]:
    """Upload test documents and return {filename: parse_response}."""
    uploaded = {}
    filenames = [
        "01_RFP_Digital_Transformation.txt",
        "02_Project_Brief_Data_Platform.txt",
        "03_SOW_v1_Original.txt",
        "05_Programme_Document_Rich.txt",
    ]

    print(f"\n{bold('── Uploading test documents ──────────────────────────────────')}")
    for fname in filenames:
        fpath = DOCS_DIR / fname
        if not fpath.exists():
            print(yellow(f"  ⚠ {fname} not found, skipping"))
            continue

        with open(fpath, "rb") as f:
            resp = client.post(
                "/api/v1/parse",
                files={"file": (fname, f, "text/plain")},
                data={"llm_provider": provider},
                headers=auth,
            )

        if resp.status_code == 200:
            data = resp.json()
            doc = data["document"]
            print(green(f"  ✓ {fname}") + f"  ({doc['word_count']} words)")
            uploaded[fname] = data
        else:
            print(red(f"  ✗ {fname}: {resp.status_code} {resp.text[:100]}"))

        time.sleep(0.3)

    return uploaded


# ── RAG accuracy ──────────────────────────────────────────────────────────────

def run_rag_eval(
    client: httpx.Client,
    auth: dict,
    uploaded: dict,
    provider: str,
    model: str | None,
) -> dict:
    print(f"\n{bold('── RAG Accuracy Evaluation ───────────────────────────────────')}")

    groups = {
        "Programme (NHS DPR)": (PROGRAMME_QUESTIONS, "05_Programme_Document_Rich.txt"),
        "RFP (Meridian Housing)": (RFP_QUESTIONS,    "01_RFP_Digital_Transformation.txt"),
        "Project Brief (CFSL)":  (BRIEF_QUESTIONS,   "02_Project_Brief_Data_Platform.txt"),
        "SOW (Northgate)":       (SOW_QUESTIONS,     "03_SOW_v1_Original.txt"),
    }

    total_pass = total_fail = 0
    group_results = {}

    for group_name, (questions, doc_file) in groups.items():
        if doc_file not in uploaded:
            print(yellow(f"\n  ⚠ {group_name}: document not uploaded, skipping"))
            continue

        project_id = uploaded[doc_file].get("project_id")
        passed = 0
        failures = []

        print(f"\n  {bold(group_name)}")
        for qa in questions:
            chat_payload = {
                "question": qa["question"],
                "llm_provider": provider,
                "project_id": project_id,
            }
            if model:
                chat_payload["llm_model"] = model

            try:
                resp = client.post("/api/v1/chat", json=chat_payload, headers=auth)
                resp.raise_for_status()
                answer = resp.json()["answer"]
            except Exception as e:
                print(red(f"    ✗ {qa['id']}: error — {e}"))
                failures.append(qa["id"])
                time.sleep(1)
                continue

            ok, missing = check_answer(answer, qa["expected_contains"])
            if ok:
                passed += 1
                print(green(f"    ✓ {qa['id']}") + f": {qa['question'][:60]}…")
            else:
                print(red(f"    ✗ {qa['id']}") + f": {qa['question'][:60]}…")
                print(f"      Missing: {missing}")
                print(f"      Answer:  {answer[:120]}…")
                failures.append(qa["id"])

            time.sleep(0.8)

        total = len(questions)
        recall = passed / total if total else 0
        total_pass += passed
        total_fail += (total - passed)
        group_results[group_name] = {"pass": passed, "total": total, "recall": recall}

        colour = green if recall >= 0.75 else (yellow if recall >= 0.5 else red)
        print(f"  {colour(f'  Recall: {passed}/{total} = {recall:.0%}')}")

    overall_total = total_pass + total_fail
    overall_recall = total_pass / overall_total if overall_total else 0
    return {
        "groups": group_results,
        "overall_pass": total_pass,
        "overall_total": overall_total,
        "overall_recall": overall_recall,
    }


# ── Generation quality ────────────────────────────────────────────────────────

def run_generation_eval(
    client: httpx.Client,
    auth: dict,
    uploaded: dict,
    provider: str,
    model: str | None,
) -> dict:
    print(f"\n{bold('── Generation Quality Evaluation ─────────────────────────────')}")

    # Get default rubric
    rubrics_resp = client.get("/api/v1/rubrics", headers=auth)
    rubrics = rubrics_resp.json() if rubrics_resp.status_code == 200 else []
    defaults = [r for r in rubrics if r["is_default"]]
    if not defaults:
        print(yellow("  ⚠ No default rubric found — skipping generation quality checks"))
        return {}
    rubric_id = defaults[0]["id"]
    print(f"  Using rubric: {defaults[0]['name']} (id={rubric_id})")

    results = {}
    llm_kwargs = {"llm_provider": provider, **({"llm_model": model} if model else {})}

    # ── SOW from project brief ──
    if "02_Project_Brief_Data_Platform.txt" in uploaded:
        print(f"\n  {bold('SOW — Castleford Financial Services Project Brief')}")
        parse = uploaded["02_Project_Brief_Data_Platform.txt"]
        doc = parse["document"]
        try:
            sow_resp = client.post(
                "/api/v1/generate/sow",
                json={
                    "client_name": "Castleford Financial Services",
                    "project_name": "Client Data & Analytics Platform",
                    "source_document": {"title": doc["title"], "text": doc["text"], "sections": doc["sections"]},
                    "assumptions": ["SME availability 4 hrs/week", "Read access to docs"],
                    "project_id": parse.get("project_id"),
                    **llm_kwargs,
                },
                headers=auth,
            )
            sow_resp.raise_for_status()
            sections = sow_resp.json().get("sections", [])
            sow_text = "\n\n".join(
                f"## {s['title']}\n" + "\n".join(s.get("paragraphs", []) + s.get("bullets", []))
                for s in sections
            )

            val_resp = client.post(
                "/api/v1/validate",
                json={"text": sow_text, "document_name": "QC_SOW", "rubric_id": rubric_id, **llm_kwargs},
                headers=auth,
            )
            val = val_resp.json()
            score = val["layer1"]["compliance_score"]
            verdict = val["overall_verdict"]
            colour = green if score >= 70 else (yellow if score >= 55 else red)
            print(colour(f"    Score: {score:.1f}%  [{verdict}]"))
            if val["layer1"].get("issues"):
                for issue in val["layer1"]["issues"][:3]:
                    print(f"    ⚠ {issue}")
            results["SOW"] = {"score": score, "verdict": verdict}
        except Exception as e:
            print(red(f"    ✗ SOW eval failed: {e}"))

    # ── Bid from RFP ──
    if "01_RFP_Digital_Transformation.txt" in uploaded:
        print(f"\n  {bold('Bid — Meridian Housing Association RFP')}")
        parse = uploaded["01_RFP_Digital_Transformation.txt"]
        doc = parse["document"]
        try:
            bid_resp = client.post(
                "/api/v1/generate/bid",
                json={
                    "client_name": "Meridian Housing Association",
                    "opportunity_title": "Digital Transformation Programme — Back-Office Operations",
                    "source_document": {"title": doc["title"], "text": doc["text"], "sections": doc["sections"]},
                    "our_strengths": ["Housing sector expertise", "UK-based delivery team", "Fixed-price model"],
                    "project_id": parse.get("project_id"),
                    **llm_kwargs,
                },
                headers=auth,
            )
            bid_resp.raise_for_status()
            sections = bid_resp.json().get("sections", [])
            bid_text = "\n\n".join(
                f"## {s['title']}\n" + "\n".join(s.get("paragraphs", []) + s.get("bullets", []))
                for s in sections
            )

            val_resp = client.post(
                "/api/v1/validate",
                json={"text": bid_text, "document_name": "QC_Bid", "rubric_id": rubric_id, **llm_kwargs},
                headers=auth,
            )
            val = val_resp.json()
            score = val["layer1"]["compliance_score"]
            verdict = val["overall_verdict"]
            colour = green if score >= 70 else (yellow if score >= 55 else red)
            print(colour(f"    Score: {score:.1f}%  [{verdict}]"))
            if val["layer1"].get("issues"):
                for issue in val["layer1"]["issues"][:3]:
                    print(f"    ⚠ {issue}")
            results["Bid"] = {"score": score, "verdict": verdict}
        except Exception as e:
            print(red(f"    ✗ Bid eval failed: {e}"))

    return results


# ── Summary report ────────────────────────────────────────────────────────────

def print_summary(rag_results: dict, gen_results: dict) -> int:
    print(f"\n{bold('═' * 58)}")
    print(bold("  QUALITY CHECK SUMMARY"))
    print(bold('═' * 58))

    exit_code = 0

    if rag_results:
        recall = rag_results.get("overall_recall", 0)
        total  = rag_results.get("overall_total", 0)
        passed = rag_results.get("overall_pass", 0)
        colour = green if recall >= 0.75 else (yellow if recall >= 0.5 else red)
        print(f"\n  RAG Recall      {colour(f'{passed}/{total}  ({recall:.0%})')}")

        for name, r in rag_results.get("groups", {}).items():
            c = green if r["recall"] >= 0.75 else (yellow if r["recall"] >= 0.5 else red)
            print(f"    {name:<30} {c(f\"{r['pass']}/{r['total']}  ({r['recall']:.0%})\")}")

        if recall < 0.75:
            exit_code = 1

    if gen_results:
        print(f"\n  Generation Quality")
        for doc_type, r in gen_results.items():
            score = r["score"]
            colour = green if score >= 70 else (yellow if score >= 55 else red)
            print(f"    {doc_type:<30} {colour(f\"{score:.1f}%  [{r['verdict']}]\")}")
            if score < 65:
                exit_code = 1

    print()
    if exit_code == 0:
        print(green("  ✓ All checks passed"))
    else:
        print(red("  ✗ Some checks failed — see details above"))
    print(bold('═' * 58) + "\n")

    return exit_code


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="BSBI Platform Quality Check")
    parser.add_argument("--provider", default=os.getenv("EVAL_LLM_PROVIDER", "openai"))
    parser.add_argument("--model",    default=os.getenv("EVAL_LLM_MODEL", None))
    parser.add_argument("--rag-only", action="store_true")
    parser.add_argument("--gen-only", action="store_true")
    args = parser.parse_args()

    print(bold(f"\nBSBI Document Intelligence Platform — Quality Check"))
    print(f"Server:   {BASE_URL}")
    print(f"Provider: {args.provider}" + (f"  Model: {args.model}" if args.model else ""))

    with httpx.Client(base_url=BASE_URL, timeout=180.0) as client:
        token = get_token(client)
        auth  = {"Authorization": f"Bearer {token}"}

        uploaded = upload_documents(client, auth, args.provider)
        if not uploaded:
            print(red("No documents uploaded — cannot proceed"))
            return 1

        rag_results = {}
        gen_results = {}

        if not args.gen_only:
            rag_results = run_rag_eval(client, auth, uploaded, args.provider, args.model)

        if not args.rag_only:
            gen_results = run_generation_eval(client, auth, uploaded, args.provider, args.model)

    return print_summary(rag_results, gen_results)


if __name__ == "__main__":
    sys.exit(main())