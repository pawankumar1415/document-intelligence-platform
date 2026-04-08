from __future__ import annotations

from backend.app.models.schemas import (
    AnalyticsDashboard,
    AnalyticsOverview,
    CommonIssue,
    ActivityItem,
    ValidationTrendPoint,
)
from backend.app.services import persistence


def get_dashboard(user_id: int) -> AnalyticsDashboard:
    overview_raw = persistence.get_analytics_overview(user_id)
    trends_raw = persistence.get_validation_trends(user_id, days=30)
    issues_raw = persistence.get_common_issues(user_id, limit=10)
    activity_raw = persistence.get_recent_activity(user_id, limit=20)

    return AnalyticsDashboard(
        overview=AnalyticsOverview(**overview_raw),
        validation_trends=[ValidationTrendPoint(**t) for t in trends_raw],
        common_issues=[CommonIssue(**i) for i in issues_raw],
        recent_activity=[ActivityItem(**a) for a in activity_raw],
    )