"""Tests for chat_service.py — RAG chat over reference narratives."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from backend.app.services.chat_service import (
    _build_context,
    _extract_period_filter,
)


class TestExtractPeriodFilter:
    def test_standard_hyphen_format(self) -> None:
        assert _extract_period_filter("What happened in P-06?") == "P-06"

    def test_no_hyphen_format(self) -> None:
        assert _extract_period_filter("P07 projects") == "P-07"

    def test_with_space(self) -> None:
        assert _extract_period_filter("P 08 status") == "P-08"

    def test_case_insensitive(self) -> None:
        assert _extract_period_filter("p-12 summary") == "P-12"

    def test_single_digit_period(self) -> None:
        assert _extract_period_filter("period P-6 results") == "P-06"

    def test_no_period_returns_none(self) -> None:
        assert _extract_period_filter("What are the key risks?") is None

    def test_period_in_middle_of_text(self) -> None:
        assert _extract_period_filter("Compare P-06 vs P-07 costs") == "P-06"

    def test_unrelated_p_number_not_matched(self) -> None:
        # "P123" — more than 2 digits — should not match
        result = _extract_period_filter("see section P123 for details")
        assert result is None


class TestBuildContext:
    def test_empty_matches_returns_empty_string(self) -> None:
        result = _build_context([])
        assert result == ""

    def test_single_match_formats_correctly(self) -> None:
        match = MagicMock()
        match.unique_id = "PROJ-001"
        match.narrative_text = "Project is on track with no issues."
        result = _build_context([match])
        assert "[1]" in result
        assert "PROJ-001" in result
        assert "Project is on track" in result

    def test_multiple_matches_numbered(self) -> None:
        matches = []
        for i in range(3):
            m = MagicMock()
            m.unique_id = f"PROJ-{i:03d}"
            m.narrative_text = f"Narrative text {i}."
            matches.append(m)
        result = _build_context(matches)
        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" in result

    def test_long_narrative_truncated_at_800(self) -> None:
        match = MagicMock()
        match.unique_id = "LONG-001"
        match.narrative_text = "x" * 2000
        result = _build_context([match])
        # Should contain only first 800 chars of narrative
        assert "x" * 800 in result
        assert "x" * 801 not in result

    def test_matches_separated_by_delimiter(self) -> None:
        matches = [MagicMock(), MagicMock()]
        for i, m in enumerate(matches):
            m.unique_id = f"P{i}"
            m.narrative_text = f"Text {i}"
        result = _build_context(matches)
        assert "---" in result


class TestRunChat:
    @patch("backend.app.services.chat_service.generate_text")
    @patch("backend.app.services.chat_service.query_all_narratives")
    @patch("backend.app.services.chat_service.embed_query")
    def test_run_chat_returns_reply_and_sources(
        self,
        mock_embed: MagicMock,
        mock_query: MagicMock,
        mock_generate: MagicMock,
    ) -> None:
        mock_embed.return_value = [0.1] * 768
        match = MagicMock()
        match.unique_id = "PROJ-001"
        match.narrative_text = "Reference narrative content."
        match.score = 0.91
        mock_query.return_value = [match]
        mock_generate.return_value = "Based on the narratives, the project is Amber."

        from backend.app.services.chat_service import run_chat

        result = run_chat(
            user_id=1,
            messages=[{"role": "user", "content": "What is the RAG status of PROJ-001?"}],
            provider="openai",
        )

        assert result["reply"] == "Based on the narratives, the project is Amber."
        assert len(result["sources"]) == 1
        assert result["sources"][0]["unique_id"] == "PROJ-001"
        assert result["sources"][0]["score"] == pytest.approx(0.91, rel=0.001)
        assert len(result["sources"][0]["excerpt"]) <= 300

    @patch("backend.app.services.chat_service.generate_text")
    @patch("backend.app.services.chat_service.query_all_narratives")
    @patch("backend.app.services.chat_service.embed_query")
    def test_run_chat_no_matches_still_responds(
        self,
        mock_embed: MagicMock,
        mock_query: MagicMock,
        mock_generate: MagicMock,
    ) -> None:
        mock_embed.return_value = [0.0] * 768
        mock_query.return_value = []
        mock_generate.return_value = "No references found; answering from general knowledge."

        from backend.app.services.chat_service import run_chat

        result = run_chat(
            user_id=1,
            messages=[{"role": "user", "content": "Any updates?"}],
        )

        assert result["reply"] != ""
        assert result["sources"] == []
        # System prompt should include no-reference message
        call_args = mock_generate.call_args
        messages_passed = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        system_content = next(m["content"] for m in messages_passed if m["role"] == "system")
        assert "No reference" in system_content

    @patch("backend.app.services.chat_service.embed_query")
    def test_run_chat_retrieval_failure_raises(self, mock_embed: MagicMock) -> None:
        mock_embed.side_effect = RuntimeError("Embedding service unavailable")

        from backend.app.services.chat_service import run_chat

        with pytest.raises(RuntimeError, match="Failed to search reference library"):
            run_chat(
                user_id=1,
                messages=[{"role": "user", "content": "Test question"}],
            )

    def test_run_chat_empty_messages_raises(self) -> None:
        from backend.app.services.chat_service import run_chat

        with pytest.raises(ValueError, match="messages list is empty"):
            run_chat(user_id=1, messages=[])

    @patch("backend.app.services.chat_service.generate_text")
    @patch("backend.app.services.chat_service.query_all_narratives")
    @patch("backend.app.services.chat_service.embed_query")
    def test_run_chat_uses_last_user_message_for_query(
        self,
        mock_embed: MagicMock,
        mock_query: MagicMock,
        mock_generate: MagicMock,
    ) -> None:
        mock_embed.return_value = [0.1] * 768
        mock_query.return_value = []
        mock_generate.return_value = "Answer."

        from backend.app.services.chat_service import run_chat

        run_chat(
            user_id=1,
            messages=[
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
                {"role": "user", "content": "Follow-up question"},
            ],
        )

        embedded_text = mock_embed.call_args[0][0]
        assert "Follow-up question" in embedded_text

    @patch("backend.app.services.chat_service.generate_text")
    @patch("backend.app.services.chat_service.query_all_narratives")
    @patch("backend.app.services.chat_service.embed_query")
    def test_run_chat_passes_full_history_to_llm(
        self,
        mock_embed: MagicMock,
        mock_query: MagicMock,
        mock_generate: MagicMock,
    ) -> None:
        mock_embed.return_value = [0.1] * 768
        mock_query.return_value = []
        mock_generate.return_value = "Answer."

        from backend.app.services.chat_service import run_chat

        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
        ]
        run_chat(user_id=1, messages=history)

        call_args = mock_generate.call_args
        messages_passed = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        roles = [m["role"] for m in messages_passed]
        assert "system" in roles
        assert roles.count("user") == 2
        assert roles.count("assistant") == 1

    @patch("backend.app.services.chat_service.generate_text")
    @patch("backend.app.services.chat_service.query_all_narratives")
    @patch("backend.app.services.chat_service.embed_query")
    def test_run_chat_source_excerpt_max_300_chars(
        self,
        mock_embed: MagicMock,
        mock_query: MagicMock,
        mock_generate: MagicMock,
    ) -> None:
        mock_embed.return_value = [0.1] * 768
        match = MagicMock()
        match.unique_id = "X"
        match.narrative_text = "y" * 500
        match.score = 0.8
        mock_query.return_value = [match]
        mock_generate.return_value = "Ok."

        from backend.app.services.chat_service import run_chat

        result = run_chat(user_id=1, messages=[{"role": "user", "content": "Q"}])
        assert len(result["sources"][0]["excerpt"]) == 300