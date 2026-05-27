"""
drift_service.py — AI performance drift detection and audit reporting.

Reads the score_audit table to produce drift metrics:
  - Daily average compliance score (last N days)
  - Verdict distribution per day
  - Provider/model change timeline
  - Score variance and linear trend direction
  - Custom rules and financial check adoption rates
"""
from __future__ import annotations

import csv
import io
import statistics
from typing import Any

from backend.app.services import persistence


def _linear_trend(values: list[float]) -> str:
    """Return 'improving', 'declining', or 'stable' based on linear regression slope."""
    n = len(values)
    if n < 3:
        return "stable"
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return "stable"
    slope = num / den
    if slope > 0.05:
        return "improving"
    if slope < -0.05:
        return "declining"
    return "stable"


def get_drift_metrics(user_id: int, days: int = 30) -> dict[str, Any]:
    """Return drift metrics dict for the dashboard."""
    # Clean up records older than retention window
    persistence.purge_old_audit_records(user_id, days=days)
    records = persistence.get_audit_records(user_id, days=days)

    if not records:
        return {
            "period_days": days,
            "total_scored": 0,
            "data_points": [],
            "provider_changes": [],
            "score_variance": 0.0,
            "trend_direction": "stable",
            "model_distribution": {},
            "avg_score": 0.0,
            "custom_rules_usage_pct": 0.0,
            "financial_check_usage_pct": 0.0,
        }

    # ── Daily aggregates ──────────────────────────────────────────────────────
    daily: dict[str, list[dict]] = {}
    for r in records:
        day = str(r["scored_at"])[:10]
        daily.setdefault(day, []).append(r)

    data_points = []
    for day in sorted(daily):
        day_recs = daily[day]
        scores = [r["compliance_score"] for r in day_recs if r["compliance_score"] is not None]
        verdicts = [r["verdict"] for r in day_recs]
        providers = [
            f"{r['provider']}/{r['model_name']}"
            for r in day_recs if r.get("provider")
        ]
        data_points.append({
            "date": day,
            "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
            "pass_count": verdicts.count("PASS"),
            "warn_count": verdicts.count("PASS_WITH_WARNINGS"),
            "fail_count": verdicts.count("FAIL"),
            "total": len(day_recs),
            "primary_provider": max(set(providers), key=providers.count) if providers else None,
        })

    # ── Provider change timeline ───────────────────────────────────────────────
    provider_changes: list[dict] = []
    prev = None
    seen: set[str] = set()
    for r in records:
        curr = f"{r['provider']}/{r['model_name']}"
        if prev and curr != prev:
            key = f"{str(r['scored_at'])[:10]}|{prev}|{curr}"
            if key not in seen:
                seen.add(key)
                provider_changes.append({
                    "date": str(r["scored_at"])[:10],
                    "from_provider": prev,
                    "to_provider": curr,
                })
        prev = curr

    # ── Overall stats ──────────────────────────────────────────────────────────
    all_scores = [r["compliance_score"] for r in records if r["compliance_score"] is not None]
    variance = round(statistics.stdev(all_scores), 3) if len(all_scores) > 1 else 0.0

    model_dist: dict[str, int] = {}
    for r in records:
        key = f"{r['provider']}/{r['model_name']}" if r.get("provider") else "unknown"
        model_dist[key] = model_dist.get(key, 0) + 1

    total = len(records)
    custom_count = sum(1 for r in records if r.get("has_custom_rules"))
    financial_count = sum(1 for r in records if r.get("has_financial_data"))

    return {
        "period_days": days,
        "total_scored": total,
        "data_points": data_points,
        "provider_changes": provider_changes,
        "score_variance": variance,
        "trend_direction": _linear_trend(all_scores),
        "model_distribution": model_dist,
        "avg_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0,
        "custom_rules_usage_pct": round(custom_count / total * 100, 1) if total else 0.0,
        "financial_check_usage_pct": round(financial_count / total * 100, 1) if total else 0.0,
    }


def export_audit_csv(user_id: int, days: int = 30) -> str:
    """Return audit records for the period as a CSV string."""
    records = persistence.get_audit_records(user_id, days=days)
    output = io.StringIO()
    fields = [
        "scored_at", "unique_id", "verdict", "compliance_score",
        "layer2_abnormality_count", "layer3_discrepancy_count",
        "provider", "model_name", "prompt_hash",
        "has_custom_rules", "has_financial_data",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for r in records:
        writer.writerow({k: r.get(k, "") for k in fields})
    return output.getvalue()