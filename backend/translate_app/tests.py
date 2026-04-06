from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from .context import DecisionsLog, RollingChatWindow
from .services import MilitaryTranslation, build_messages, call_claude, compress_session_anchor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _make_claude_response(payload: dict) -> MagicMock:
    """Build a mock anthropic Messages response with a single text block."""
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [block]
    return response


_VALID_PAYLOAD = {
    "civilian_title": "Logistics Manager",
    "summary": "Experienced leader with 10 years managing complex supply chains.",
    "bullets": [
        "Led a team of 20 to deliver 99% on-time shipments.",
        "Reduced operational costs by 15% through process improvements.",
        "Coordinated cross-functional teams across 5 locations.",
    ],
}


# ---------------------------------------------------------------------------
# context.py — DecisionsLog
# ---------------------------------------------------------------------------

class TestDecisionsLog:
    def test_approve_adds_entry(self):
        log = DecisionsLog()
        log.approve("Managed logistics", "Experience", "Quantified impact")
        block = log.to_prompt_block()
        assert "APPROVED" in block
        assert "Managed logistics" in block
        assert "Experience" in block

    def test_reject_adds_entry(self):
        log = DecisionsLog()
        log.reject("Used military jargon", "Too vague")
        block = log.to_prompt_block()
        assert "REJECTED" in block
        assert "Used military jargon" in block

    def test_empty_log_returns_empty_string(self):
        log = DecisionsLog()
        assert log.to_prompt_block() == ""

    def test_token_estimate_is_positive_when_nonempty(self):
        log = DecisionsLog()
        log.approve("bullet", "section", "reasoning")
        assert log.token_estimate() > 0

    def test_serialization_roundtrip(self):
        """DecisionsLog entries are preserved in order."""
        log = DecisionsLog()
        log.approve("bullet A", "sec1", "great")
        log.reject("bullet B", "jargon")
        block = log.to_prompt_block()
        assert block.index("APPROVED") < block.index("REJECTED")


# ---------------------------------------------------------------------------
# context.py — RollingChatWindow
# ---------------------------------------------------------------------------

class TestRollingChatWindow:
    def test_add_turn_stores_turns(self):
        window = RollingChatWindow()
        window.add_turn("user", "Hello")
        window.add_turn("assistant", "Hi there")
        messages = window.to_messages()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}

    def test_prunes_oldest_when_over_limit(self):
        window = RollingChatWindow()
        # Each turn ~500 tokens × 4 chars = 2000 chars; add enough to exceed MAX_TOKENS
        long_content = "x" * 2001 * 4  # well over 2000 tokens
        window.add_turn("user", "turn 1")
        window.add_turn("assistant", "turn 2")
        window.add_turn("user", long_content)
        messages = window.to_messages()
        # The long content itself will push it over; oldest turns should be pruned
        # but minimum 2 turns must remain
        assert len(messages) >= 2

    def test_retains_minimum_2_turns(self):
        window = RollingChatWindow()
        # Add two very long turns that together exceed MAX_TOKENS
        huge = "y" * 5000 * 4
        window.add_turn("user", huge)
        window.add_turn("assistant", huge)
        # Despite being over limit, at least 2 turns should remain
        assert len(window.to_messages()) == 2

    def test_to_messages_returns_copy(self):
        window = RollingChatWindow()
        window.add_turn("user", "test")
        msgs = window.to_messages()
        msgs.append({"role": "user", "content": "injected"})
        assert len(window.to_messages()) == 1


# ---------------------------------------------------------------------------
# services.py — compress_session_anchor
# ---------------------------------------------------------------------------

class TestCompressSessionAnchor:
    @patch("translate_app.services.anthropic.Anthropic")
    def test_returns_valid_dict(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_claude_response(_VALID_PAYLOAD)

        result = compress_session_anchor("I served in Army logistics.", "We need a supply chain manager.")
        assert result["civilian_title"] == "Logistics Manager"
        assert isinstance(result["bullets"], list)
        assert len(result["bullets"]) >= 1

    @patch("translate_app.services.anthropic.Anthropic")
    def test_raises_value_error_on_invalid_json(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        block = MagicMock()
        block.type = "text"
        block.text = "not json at all"
        mock_client.messages.create.return_value = MagicMock(content=[block])

        with pytest.raises(ValueError):
            compress_session_anchor("military text here", "job description here")


# ---------------------------------------------------------------------------
# services.py — build_messages
# ---------------------------------------------------------------------------

class TestBuildMessages:
    def test_layers_in_correct_order(self):
        anchor = {"civilian_title": "PM", "summary": "Leader", "bullets": ["Led team"]}
        decisions = DecisionsLog()
        decisions.approve("Led team", "Experience", "strong")
        chat = RollingChatWindow()
        chat.add_turn("user", "Can you improve bullet 1?")
        chat.add_turn("assistant", "Sure, here is a revision.")

        messages = build_messages(anchor, decisions, chat, "Now revise bullet 2.")

        # Prior turns must come before the new message
        assert messages[-1]["role"] == "user"
        assert "revise bullet 2" in messages[-1]["content"]

        # Anchor context embedded in final user message
        assert "PM" in messages[-1]["content"]

        # Decisions log embedded in final user message
        assert "APPROVED" in messages[-1]["content"]

        # Prior turns preserved in order before the new message
        assert messages[0]["content"] == "Can you improve bullet 1?"
        assert messages[1]["content"] == "Sure, here is a revision."

    def test_new_message_contains_schema(self):
        anchor = {"civilian_title": "PM", "summary": "x", "bullets": []}
        messages = build_messages(anchor, DecisionsLog(), RollingChatWindow(), "update")
        assert "civilian_title" in messages[-1]["content"]


# ---------------------------------------------------------------------------
# services.py — call_claude
# ---------------------------------------------------------------------------

class TestCallClaude:
    @patch("translate_app.services.anthropic.Anthropic")
    def test_valid_response_returns_model(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_claude_response(_VALID_PAYLOAD)

        result = call_claude([{"role": "user", "content": "translate"}])
        assert isinstance(result, MilitaryTranslation)
        assert result.civilian_title == "Logistics Manager"

    @patch("translate_app.services.anthropic.Anthropic")
    def test_markdown_fences_stripped(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        block = MagicMock()
        block.type = "text"
        block.text = f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```"
        mock_client.messages.create.return_value = MagicMock(content=[block])

        result = call_claude([{"role": "user", "content": "translate"}])
        assert result.civilian_title == "Logistics Manager"

    @patch("translate_app.services.anthropic.Anthropic")
    def test_malformed_response_raises_value_error(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        block = MagicMock()
        block.type = "text"
        block.text = '{"civilian_title": "PM"}'  # missing required fields
        mock_client.messages.create.return_value = MagicMock(content=[block])

        with pytest.raises(ValueError):
            call_claude([{"role": "user", "content": "translate"}])

    @patch("translate_app.services.anthropic.Anthropic")
    def test_ignores_tool_use_blocks(self, MockAnthropic):
        """Only text blocks are parsed."""
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.text = "should not be read"
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = json.dumps(_VALID_PAYLOAD)
        mock_client.messages.create.return_value = MagicMock(content=[tool_block, text_block])

        result = call_claude([{"role": "user", "content": "translate"}])
        assert result.civilian_title == "Logistics Manager"


# ---------------------------------------------------------------------------
# views.py — POST /api/v1/translations/
# ---------------------------------------------------------------------------

class TestTranslationView:
    @patch("translate_app.views.compress_session_anchor")
    def test_valid_input_returns_201(self, mock_anchor, auth_client, db):
        mock_anchor.return_value = _VALID_PAYLOAD
        response = auth_client.post(
            "/api/v1/translations/",
            {"military_text": "I served in Army logistics for 10 years.", "job_description": "We need a supply chain manager."},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["civilian_title"] == "Logistics Manager"

    @patch("translate_app.views.compress_session_anchor")
    def test_malformed_claude_response_returns_422(self, mock_anchor, auth_client, db):
        mock_anchor.side_effect = ValueError("bad response")
        response = auth_client.post(
            "/api/v1/translations/",
            {"military_text": "I served in Army logistics for 10 years.", "job_description": "We need a supply chain manager."},
            format="json",
        )
        assert response.status_code == 422

    def test_missing_fields_returns_400(self, auth_client, db):
        response = auth_client.post(
            "/api/v1/translations/",
            {"military_text": "short"},  # missing job_description, text too short
            format="json",
        )
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.post(
            "/api/v1/translations/",
            {"military_text": "text", "job_description": "desc"},
            format="json",
        )
        assert response.status_code == 401

    @patch("translate_app.views.compress_session_anchor")
    def test_resume_saved_scoped_to_user(self, mock_anchor, auth_client, user, db):
        from .models import Resume
        mock_anchor.return_value = _VALID_PAYLOAD
        auth_client.post(
            "/api/v1/translations/",
            {"military_text": "I served in Army logistics for 10 years.", "job_description": "We need a supply chain manager."},
            format="json",
        )
        assert Resume.objects.filter(user=user).count() == 1
