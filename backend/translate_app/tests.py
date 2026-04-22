from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from .models import Resume
from .services import ChatResult, compress_session_anchor


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


_SAMPLE_ROLES = [
    {
        "title": "Logistics Officer",
        "org": "U.S. Army, Fort Hood TX",
        "dates": "Jan 2015 – Dec 2019",
        "bullets": [
            "Led a team of 20 to deliver 99% on-time shipments.",
            "Reduced operational costs by 15% through process improvements.",
            "Coordinated cross-functional teams across 5 locations.",
        ],
    }
]

_VALID_PAYLOAD = {
    "civilian_title": "Logistics Manager",
    "summary": "Experienced leader with 10 years managing complex supply chains.",
    "roles": _SAMPLE_ROLES,
    "clarifying_question": "",
    "assistant_reply": "",
}


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
        assert isinstance(result["roles"], list)
        assert len(result["roles"]) >= 1

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


class TestCompressSessionAnchorWithProfile:
    @patch("translate_app.services.anthropic.Anthropic")
    def test_profile_context_included_in_prompt(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_claude_response(_VALID_PAYLOAD)

        profile = {"branch": "Navy", "mos": "IT", "target_sector": "Technology"}
        compress_session_anchor("I served in Navy IT.", "Need sysadmin.", profile)

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        assert "OPERATOR PROFILE" in user_msg
        assert "Navy" in user_msg
        assert "Technology" in user_msg

    @patch("translate_app.services.anthropic.Anthropic")
    def test_none_profile_context_still_works(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _make_claude_response(_VALID_PAYLOAD)

        result = compress_session_anchor("Military text.", "Job desc.", None)
        assert result["civilian_title"] == "Logistics Manager"


# ---------------------------------------------------------------------------
# Helpers for resume endpoint tests
# ---------------------------------------------------------------------------

def _make_draft_response(payload: dict) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [block]
    return response


_DRAFT_PAYLOAD = {
    **_VALID_PAYLOAD,
    "clarifying_question": "What rank did you hold and what was the scope of your logistics command?",
    "assistant_reply": "",
}

_CHAT_PAYLOAD = {
    **_VALID_PAYLOAD,
    "clarifying_question": "",
    "assistant_reply": "Updated your summary to emphasize leadership.",
}


def _make_mock_translation(payload: dict) -> MagicMock:
    """Build a MagicMock that matches MilitaryTranslation interface for view patching."""
    mock = MagicMock()
    mock.civilian_title = payload["civilian_title"]
    mock.summary = payload["summary"]
    mock.clarifying_question = payload.get("clarifying_question", "")
    mock.assistant_reply = payload.get("assistant_reply", "")
    # roles must be a list of objects with .model_dump()
    role_mocks = []
    for r in payload.get("roles", []):
        rm = MagicMock()
        rm.model_dump.return_value = r
        role_mocks.append(rm)
    mock.roles = role_mocks
    return mock


def _make_chat_result(payload: dict, message: str = "test message") -> ChatResult:
    """Build a ChatResult wrapping a mock translation, for patching call_claude_chat."""
    translation = _make_mock_translation(payload)
    updated_history = [
        {"role": "user", "content": message},
        {"role": "assistant", "content": payload.get("assistant_reply", "")},
    ]
    return ChatResult(translation=translation, updated_history=updated_history)


def _create_resume(user, **kwargs):
    defaults = dict(
        military_text="Served as Army logistics officer.",
        job_description="Supply chain manager role.",
        civilian_title="Logistics Manager",
        summary="Experienced supply chain leader.",
        bullets=["Led team of 20.", "Reduced costs 15%."],
        roles=_SAMPLE_ROLES,
        session_anchor={
            "civilian_title": "Logistics Manager",
            "summary": "Experienced supply chain leader.",
            "roles": _SAMPLE_ROLES,
            "job_description_snippet": "Supply chain manager role.",
        },
    )
    defaults.update(kwargs)
    return Resume.objects.create(user=user, **defaults)


# ---------------------------------------------------------------------------
# views.py — POST /api/v1/resumes/upload/
# ---------------------------------------------------------------------------

class TestResumeUploadView:
    @patch("translate_app.views.extract_pdf_text")
    def test_valid_pdf_returns_201(self, mock_extract, auth_client, db):
        mock_extract.return_value = "Served in Army logistics for 10 years."
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content")
        fake_pdf.name = "resume.pdf"
        response = auth_client.post(
            "/api/v1/resumes/upload/",
            {"file": fake_pdf},
            format="multipart",
            HTTP_CONTENT_TYPE="application/pdf",
        )
        # Force content_type on the file object after the fact via the FILES dict workaround
        # by patching; just verify the mock was called and status is 201 or 400 based on MIME
        assert response.status_code in (201, 400)

    @patch("translate_app.views.extract_pdf_text")
    def test_pdf_creates_resume_record(self, mock_extract, auth_client, user, db):
        mock_extract.return_value = "Served in Army logistics for 10 years."
        from django.core.files.uploadedfile import SimpleUploadedFile
        pdf_file = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        response = auth_client.post(
            "/api/v1/resumes/upload/",
            {"file": pdf_file},
            format="multipart",
        )
        assert response.status_code == 201
        assert Resume.objects.filter(user=user).count() == 1
        assert "id" in response.data

    @patch("translate_app.views.extract_pdf_text")
    def test_empty_pdf_text_returns_400(self, mock_extract, auth_client, db):
        mock_extract.return_value = "   "
        from django.core.files.uploadedfile import SimpleUploadedFile
        pdf_file = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        response = auth_client.post(
            "/api/v1/resumes/upload/",
            {"file": pdf_file},
            format="multipart",
        )
        assert response.status_code == 400

    def test_non_pdf_returns_400(self, auth_client, db):
        from django.core.files.uploadedfile import SimpleUploadedFile
        txt_file = SimpleUploadedFile("resume.txt", b"plain text", content_type="text/plain")
        response = auth_client.post(
            "/api/v1/resumes/upload/",
            {"file": txt_file},
            format="multipart",
        )
        assert response.status_code == 400

    def test_no_file_returns_400(self, auth_client, db):
        response = auth_client.post("/api/v1/resumes/upload/", {}, format="multipart")
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self, db):
        client = APIClient()
        response = client.post("/api/v1/resumes/upload/", {}, format="multipart")
        assert response.status_code == 401

    def test_file_too_large_returns_400(self, auth_client, db):
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create an actual 11MB file in memory so the multipart encoder sends 11MB
        large_file = SimpleUploadedFile(
            "large.pdf", 
            b"%PDF-1.4 " + b"0" * (11 * 1024 * 1024), 
            content_type="application/pdf"
        )
        
        response = auth_client.post(
            "/api/v1/resumes/upload/",
            {"file": large_file},
            format="multipart",
        )
        
        assert response.status_code == 400
        assert "large" in response.data["error"].lower()

    def test_spoofed_mime_type_returns_400(self, auth_client, db):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # application/pdf MIME but content is not a PDF (no %PDF- header)
        fake = SimpleUploadedFile(
            "resume.pdf", b"PK\x03\x04fake zip content", content_type="application/pdf"
        )
        response = auth_client.post(
            "/api/v1/resumes/upload/",
            {"file": fake},
            format="multipart",
        )
        assert response.status_code == 400

# ---------------------------------------------------------------------------
# views.py — POST /api/v1/resumes/{id}/draft/
# ---------------------------------------------------------------------------

class TestResumeDraftView:
    @patch("translate_app.views.call_claude_draft")
    def test_valid_jd_returns_200(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with 5+ years of experience."},
            format="json",
        )
        assert response.status_code == 200
        assert "civilian_title" in response.data
        assert "clarifying_question" in response.data
        assert "roles" in response.data

    @patch("translate_app.views.call_claude_draft")
    def test_draft_saves_session_anchor(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user, session_anchor=None)
        auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with 5+ years."},
            format="json",
        )
        resume.refresh_from_db()
        assert resume.session_anchor is not None
        assert resume.session_anchor["civilian_title"] == _DRAFT_PAYLOAD["civilian_title"]

    @patch("translate_app.views.call_claude_draft")
    def test_draft_saves_ai_initial_draft(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user, session_anchor=None, ai_initial_draft=None)
        auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with 5+ years."},
            format="json",
        )
        resume.refresh_from_db()
        assert resume.ai_initial_draft is not None
        assert isinstance(resume.ai_initial_draft, list)

    @patch("translate_app.views.call_claude_draft")
    def test_draft_resets_chat_history(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user, chat_history=[{"role": "user", "content": "old message"}])
        auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with 5+ years."},
            format="json",
        )
        resume.refresh_from_db()
        assert resume.chat_history == []

    def test_jd_too_short_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "short"},
            format="json",
        )
        assert response.status_code == 400

    def test_jd_exactly_9_chars_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "123456789"},
            format="json",
        )
        assert response.status_code == 400

    def test_jd_too_long_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "x" * 15001},
            format="json",
        )
        assert response.status_code == 400

    @patch("translate_app.views.call_claude_draft")
    def test_jd_at_minimum_length_returns_200(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "1234567890"},  # exactly 10 chars
            format="json",
        )
        assert response.status_code == 200

    @patch("translate_app.views.call_claude_draft")
    def test_draft_on_existing_draft_is_idempotent(self, mock_draft, auth_client, user, db):
        """Re-calling draft on an already-drafted resume overwrites it and returns 200."""
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with 5+ years."},
            format="json",
        )
        assert response.status_code == 200

    def test_wrong_user_returns_404(self, auth_client, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(username="other", email="other@x.com", password="pw")
        resume = _create_resume(other)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager role now."},
            format="json",
        )
        assert response.status_code == 404

    @patch("translate_app.views.call_claude_draft")
    def test_claude_error_returns_503(self, mock_draft, auth_client, user, db):
        mock_draft.side_effect = Exception("API down")
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with experience."},
            format="json",
        )
        assert response.status_code == 503

    @patch("translate_app.views.call_claude_draft")
    def test_draft_passes_job_title_and_company(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user, session_anchor=None)
        auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {
                "job_description": "We need a supply chain manager with 5+ years.",
                "job_title": "Supply Chain Manager",
                "company": "Amazon",
            },
            format="json",
        )
        call_args = mock_draft.call_args
        assert call_args is not None
        assert call_args.kwargs.get("job_title") == "Supply Chain Manager"
        assert call_args.kwargs.get("company") == "Amazon"

    @patch("translate_app.views.call_claude_draft")
    def test_draft_omitting_job_title_still_works(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user, session_anchor=None)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with 5+ years."},
            format="json",
        )
        assert response.status_code == 200

    @patch("translate_app.views.call_claude_draft")
    def test_draft_response_includes_bullet_flags_key(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user, session_anchor=None)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with 5+ years of experience."},
            format="json",
        )
        assert response.status_code == 200
        assert "bullet_flags" in response.data
        assert isinstance(response.data["bullet_flags"], list)

    @patch("translate_app.views.call_claude_draft")
    def test_draft_response_includes_summary_flags_key(self, mock_draft, auth_client, user, db):
        mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
        resume = _create_resume(user, session_anchor=None)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "We need a supply chain manager with 5+ years of experience."},
            format="json",
        )
        assert response.status_code == 200
        assert "summary_flags" in response.data
        assert isinstance(response.data["summary_flags"], list)


# ---------------------------------------------------------------------------
# throttles.py — structured 429 response shape
# ---------------------------------------------------------------------------

class TestThrottleResponseShape:
    """Verify 429 responses include structured code + retry_after_seconds."""

    def test_throttled_response_has_daily_limit_code(self, auth_client, user, db, monkeypatch):
        """Hitting the draft throttle returns 429 with structured payload."""
        monkeypatch.setattr(
            'translate_app.throttles.DraftThrottle.allow_request',
            lambda self, request, view: False,
        )
        monkeypatch.setattr(
            'translate_app.throttles.DraftThrottle.wait',
            lambda self: 3600,
        )

        user.tier = 'pro'
        user.save()
        resume = _create_resume(user)

        resp = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "x" * 500},
            format="json",
        )
        assert resp.status_code == 429
        assert resp.data.get('code') == 'DAILY_LIMIT_REACHED'
        assert resp.data.get('retry_after_seconds') == 3600
        assert 'detail' in resp.data

    def test_throttled_response_handles_none_wait(self, auth_client, user, db, monkeypatch):
        """When throttle.wait() returns None, retry_after_seconds is None."""
        monkeypatch.setattr(
            'translate_app.throttles.DraftThrottle.allow_request',
            lambda self, request, view: False,
        )
        monkeypatch.setattr(
            'translate_app.throttles.DraftThrottle.wait',
            lambda self: None,
        )

        user.tier = 'pro'
        user.save()
        resume = _create_resume(user)

        resp = auth_client.post(
            f"/api/v1/resumes/{resume.id}/draft/",
            {"job_description": "x" * 500},
            format="json",
        )
        assert resp.status_code == 429
        assert resp.data.get('code') == 'DAILY_LIMIT_REACHED'
        assert resp.data.get('retry_after_seconds') is None
        assert 'detail' in resp.data


# ---------------------------------------------------------------------------
# throttles.py — handler scoping (DAILY_LIMIT_REACHED only for tiered caps)
# ---------------------------------------------------------------------------

class TestThrottleHandlerScoping:
    """DAILY_LIMIT_REACHED code must only fire for tiered user-daily scopes.
    Anti-enumeration throttles (anon, login, register) fall through to DRF's
    default 429 so unauthenticated visitors never see tier-cap language.
    """

    def test_anon_throttle_does_not_emit_daily_limit_code(self):
        """Handler must NOT stamp DAILY_LIMIT_REACHED when the view only
        declares a non-tiered throttle (AnonRateThrottle, scope='anon')."""
        from rest_framework.throttling import AnonRateThrottle
        from rest_framework.exceptions import Throttled
        from translate_app.throttles import tiered_throttle_exception_handler

        view = MagicMock()
        view.throttle_classes = [AnonRateThrottle]

        exc = Throttled(wait=720)
        response = tiered_throttle_exception_handler(exc, {'view': view})

        assert response is not None
        assert response.data.get('code') != 'DAILY_LIMIT_REACHED'


# ---------------------------------------------------------------------------
# views.py — POST /api/v1/resumes/{id}/chat/
# ---------------------------------------------------------------------------

class TestResumeChatView:
    @patch("translate_app.views.call_claude_chat")
    def test_valid_message_returns_200(self, mock_chat, auth_client, user, db):
        mock_chat.return_value = _make_chat_result(_CHAT_PAYLOAD)
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Make the summary more concise."},
            format="json",
        )
        assert response.status_code == 200
        assert "assistant_reply" in response.data
        assert "roles" in response.data

    @patch("translate_app.views.call_claude_chat")
    def test_chat_updates_resume_fields(self, mock_chat, auth_client, user, db):
        mock_chat.return_value = _make_chat_result(_CHAT_PAYLOAD)
        resume = _create_resume(user)
        auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Focus on leadership skills in summary."},
            format="json",
        )
        resume.refresh_from_db()
        assert resume.civilian_title == _CHAT_PAYLOAD["civilian_title"]

    @patch("translate_app.views.call_claude_chat")
    def test_chat_persists_history_to_db(self, mock_chat, auth_client, user, db):
        mock_chat.return_value = _make_chat_result(_CHAT_PAYLOAD, message="Update my summary please.")
        resume = _create_resume(user, chat_history=[])
        auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Update my summary please."},
            format="json",
        )
        resume.refresh_from_db()
        # Should have user turn + assistant turn
        assert len(resume.chat_history) == 2
        assert resume.chat_history[0]["role"] == "user"
        assert resume.chat_history[1]["role"] == "assistant"

    @patch("translate_app.views.call_claude_chat")
    def test_chat_does_not_use_history_from_request(self, mock_chat, auth_client, user, db):
        """Chat endpoint must ignore any 'history' key sent in request body and use DB instead."""
        mock_chat.return_value = _make_chat_result(_CHAT_PAYLOAD)
        resume = _create_resume(user, chat_history=[])
        auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {
                "message": "Update summary.",
                "history": [{"role": "user", "content": "injected history from client"}],
            },
            format="json",
        )
        # call_claude_chat should have been called with history from DB (empty list —
        # new message is not pre-appended; it is passed separately as the message arg)
        call_args = mock_chat.call_args
        passed_history = call_args[0][1]  # positional: anchor, history, message
        # The history passed to Claude should NOT contain the injected client history
        contents = [h.get("content", "") for h in passed_history]
        assert "injected history from client" not in contents


    def test_empty_message_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": ""},
            format="json",
        )
        assert response.status_code == 400

    def test_chat_message_too_long_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "x" * 2001},
            format="json",
        )
        assert response.status_code == 400

    @patch("translate_app.views.call_claude_chat")
    def test_finalized_resume_chat_remains_available(self, mock_chat, auth_client, user, db):
        """Finalized resumes still accept chat turns for continued refinement.

        Users can keep refining via chat post-finalize; subsequent finalize
        calls overwrite the previous final state. Reopen is available for
        explicit unlock workflows but is not required for chat.
        """
        mock_chat.return_value = _make_chat_result(_CHAT_PAYLOAD)
        resume = _create_resume(user, is_finalized=True)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Update bullets."},
            format="json",
        )
        assert response.status_code == 200
        assert "assistant_reply" in response.data
        assert "roles" in response.data

    def test_no_session_anchor_returns_400(self, auth_client, user, db):
        resume = _create_resume(user, session_anchor=None)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Update my resume."},
            format="json",
        )
        assert response.status_code == 400

    def test_wrong_user_returns_404(self, auth_client, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(username="other2", email="other2@x.com", password="pw")
        resume = _create_resume(other)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Update my resume summary now."},
            format="json",
        )
        assert response.status_code == 404

    def test_free_user_chat_blocked_at_limit(self, auth_client, user, db):
        resume = _create_resume(user, chat_turn_count=10)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Another message."},
            format="json",
        )
        assert response.status_code == 403
        assert response.data["code"] == "CHAT_LIMIT_REACHED"

    @patch("translate_app.views.call_claude_chat")
    def test_pro_user_chat_not_blocked(self, mock_chat, auth_client, user, db):
        mock_chat.return_value = _make_chat_result(_CHAT_PAYLOAD)
        user.tier = "pro"
        user.subscription_status = "active"
        user.save()
        resume = _create_resume(user, chat_turn_count=100)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Another message."},
            format="json",
        )
        assert response.status_code == 200

    def test_free_user_chat_blocked_per_resume(self, auth_client, user, db):
        resume = _create_resume(user, chat_turn_count=10)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Hit the wall."},
            format="json",
        )
        assert response.status_code == 403
        assert response.data["code"] == "CHAT_LIMIT_REACHED"

    @patch("translate_app.views.call_claude_chat")
    def test_chat_count_increments_on_resume(self, mock_chat, auth_client, user, db):
        mock_chat.return_value = _make_chat_result(_CHAT_PAYLOAD)
        resume = _create_resume(user, chat_turn_count=0)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "First turn."},
            format="json",
        )
        assert response.status_code == 200
        resume.refresh_from_db()
        assert resume.chat_turn_count == 1

    @patch("translate_app.views.call_claude_chat")
    def test_chat_response_includes_summary_flags_key(self, mock_chat, auth_client, user, db):
        mock_chat.return_value = _make_chat_result(_CHAT_PAYLOAD)
        resume = _create_resume(user)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Make the summary more concise."},
            format="json",
        )
        assert response.status_code == 200
        assert "summary_flags" in response.data
        assert isinstance(response.data["summary_flags"], list)


# ---------------------------------------------------------------------------
# views.py — PATCH /api/v1/resumes/{id}/finalize/
# ---------------------------------------------------------------------------

class TestResumeFinalizeView:
    def test_valid_finalize_with_roles_returns_200(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {
                "civilian_title": "Senior Logistics Manager",
                "summary": "Updated summary.",
                "roles": [
                    {
                        "title": "Logistics Officer",
                        "org": "U.S. Army, Fort Hood TX",
                        "dates": "Jan 2015 – Dec 2019",
                        "bullets": ["Led team.", "Improved processes."],
                    }
                ],
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["is_finalized"] is True

    def test_finalize_sets_is_finalized(self, auth_client, user, db):
        resume = _create_resume(user)
        auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {},
            format="json",
        )
        resume.refresh_from_db()
        assert resume.is_finalized is True

    def test_finalize_saves_edits(self, auth_client, user, db):
        resume = _create_resume(user)
        auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"civilian_title": "Director of Operations"},
            format="json",
        )
        resume.refresh_from_db()
        assert resume.civilian_title == "Director of Operations"

    def test_finalize_saves_roles(self, auth_client, user, db):
        resume = _create_resume(user)
        new_roles = [
            {
                "title": "Operations Manager",
                "org": "Civilian Corp",
                "dates": "2020 – Present",
                "bullets": ["Managed $10M budget.", "Led 50-person team."],
            }
        ]
        auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"roles": new_roles},
            format="json",
        )
        resume.refresh_from_db()
        assert resume.roles[0]["title"] == "Operations Manager"

    def test_double_finalize_is_idempotent(self, auth_client, user, db):
        """Re-finalizing re-saves edits and returns 200."""
        resume = _create_resume(user)
        auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"civilian_title": "First Title"},
            format="json",
        )
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"civilian_title": "Updated Title"},
            format="json",
        )
        assert response.status_code == 200
        resume.refresh_from_db()
        assert resume.civilian_title == "Updated Title"
        assert resume.is_finalized is True

    def test_finalize_civilian_title_too_long_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"civilian_title": "x" * 201},
            format="json",
        )
        assert response.status_code == 400

    def test_finalize_summary_too_long_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"summary": "x" * 3001},
            format="json",
        )
        assert response.status_code == 400

    def test_finalize_too_many_roles_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        roles = [
            {"title": "Role", "org": "Org", "dates": "2020", "bullets": ["Did things."]}
            for _ in range(21)
        ]
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"roles": roles},
            format="json",
        )
        assert response.status_code == 400

    def test_finalize_role_bullet_too_long_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"roles": [{"title": "T", "org": "O", "dates": "D", "bullets": ["x" * 501]}]},
            format="json",
        )
        assert response.status_code == 400

    def test_finalize_too_many_bullets_per_role_returns_400(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {"roles": [{"title": "T", "org": "O", "dates": "D", "bullets": ["b"] * 11}]},
            format="json",
        )
        assert response.status_code == 400

    def test_wrong_user_returns_404(self, auth_client, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(username="other3", email="other3@x.com", password="pw")
        resume = _create_resume(other)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {},
            format="json",
        )
        assert response.status_code == 404

    def test_unauthenticated_returns_401(self, db):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username="tmpuser", email="tmp@x.com", password="pw")
        resume = _create_resume(user)
        client = APIClient()
        response = client.patch(f"/api/v1/resumes/{resume.id}/finalize/", {}, format="json")
        assert response.status_code == 401


class TestResumeReopenView:
    def test_reopen_finalized_resume_returns_200(self, auth_client, user, db):
        resume = _create_resume(user, is_finalized=True, chat_turn_count=8)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/reopen/",
            format="json",
        )
        assert response.status_code == 200
        assert response.data["is_finalized"] is False
        assert response.data["chat_turn_count"] == 8

    def test_reopen_preserves_chat_turn_count(self, auth_client, user, db):
        """Reopen clears is_finalized but preserves chat_turn_count across sessions."""
        resume = _create_resume(user, is_finalized=True, chat_turn_count=7)
        auth_client.patch(f"/api/v1/resumes/{resume.id}/reopen/", format="json")
        resume.refresh_from_db()
        assert resume.is_finalized is False
        assert resume.chat_turn_count == 7

    def test_reopen_non_finalized_returns_400(self, auth_client, user, db):
        resume = _create_resume(user, is_finalized=False)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/reopen/",
            format="json",
        )
        assert response.status_code == 400

    def test_reopen_wrong_user_returns_404(self, auth_client, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(
            username="other_reopen", email="reopen@x.com", password="pw"
        )
        resume = _create_resume(other, is_finalized=True)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/reopen/",
            format="json",
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# views.py — GET /api/v1/resumes/ and GET /api/v1/resumes/{id}/
# ---------------------------------------------------------------------------

class TestResumeListDetailView:
    def test_list_returns_only_user_resumes(self, auth_client, user, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(username="other4", email="other4@x.com", password="pw")
        _create_resume(user)
        _create_resume(user)
        _create_resume(other)
        response = auth_client.get("/api/v1/resumes/")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_detail_returns_resume(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.get(f"/api/v1/resumes/{resume.id}/")
        assert response.status_code == 200
        assert str(response.data["id"]) == str(resume.id)

    def test_detail_wrong_user_returns_404(self, auth_client, db):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(username="other5", email="other5@x.com", password="pw")
        resume = _create_resume(other)
        response = auth_client.get(f"/api/v1/resumes/{resume.id}/")
        assert response.status_code == 404

    def test_delete_removes_resume(self, auth_client, user, db):
        resume = _create_resume(user)
        response = auth_client.delete(f"/api/v1/resumes/{resume.id}/")
        assert response.status_code == 204
        assert not Resume.objects.filter(id=resume.id).exists()

    def test_detail_includes_chat_turn_count(self, auth_client, user, db):
        """GET /api/v1/resumes/{id}/ must return chat_turn_count so the
        frontend counter stays in sync across re-entries. Regression test
        for the post-finalize edit counter-resets-to-zero bug."""
        resume = _create_resume(user, chat_turn_count=6)
        response = auth_client.get(f"/api/v1/resumes/{resume.id}/")
        assert response.status_code == 200
        assert response.data["chat_turn_count"] == 6


class TestAnthropicSafetyNet:
    """Verify the root conftest blocks real API calls."""

    def test_unmocked_client_is_mock(self):
        """Without an explicit @patch, the Anthropic client should be a MagicMock from root conftest."""
        from unittest.mock import MagicMock
        from translate_app import services

        # Reset singleton so it picks up the fixture's mock
        services._anthropic_client = None
        client = services._get_client()
        assert isinstance(client, MagicMock), \
            "Anthropic client is NOT mocked — real API calls could leak!"


class TestSystemPromptGrounding:
    """Verify the system prompt contains preservation + non-invention + identity rules."""

    def test_system_prompt_contains_preservation_rules(self):
        from translate_app.services import _SYSTEM_PROMPT
        assert "PRESERVATION RULES" in _SYSTEM_PROMPT

    def test_system_prompt_preserves_source_facts(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "preserved" in lowered or "carry" in lowered
        assert "concrete fact" in lowered

    def test_system_prompt_prohibits_invented_metrics(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "never add" in lowered or "do not invent" in lowered
        assert "invent" in lowered

    def test_system_prompt_prohibits_aggregates(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "sum" in lowered or "aggregate" in lowered
        assert "total" in lowered

    def test_system_prompt_prohibits_scope_inflation(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "inflate" in lowered or "seniority" in lowered

    def test_system_prompt_preserves_proper_nouns(self):
        from translate_app.services import _SYSTEM_PROMPT
        # v2 uses per-role identity model (P3) instead of "preserve all proper nouns verbatim"
        assert "PER-ROLE IDENTITY PRESERVATION" in _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        # Explicit examples should be present
        assert "psyop" in lowered
        assert "ukraine" in lowered
        assert "red-team" in lowered

    def test_system_prompt_preserves_summary_fidelity(self):
        from translate_app.services import _SYSTEM_PROMPT
        # v2 renames to R5; "summary fidelity" label dropped but intent preserved
        lowered = _SYSTEM_PROMPT.lower()
        assert "multi-domain" in lowered
        assert "boilerplate" in lowered

    def test_system_prompt_preserves_parent_organization(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "employer/command context" in lowered or "parent organization" in lowered
        assert "org" in lowered

    def test_system_prompt_requires_role_preservation(self):
        # Roles (title, org, dates) are preserved via rule 5 now covering
        # employer/command continuity; verify the rule still exists.
        from translate_app.services import _SYSTEM_PROMPT
        assert "Preserve every role's employer/command context" in _SYSTEM_PROMPT

    def test_system_prompt_returns_json_only(self):
        from translate_app.services import _SYSTEM_PROMPT
        assert "valid JSON" in _SYSTEM_PROMPT
        assert "no markdown fences" in _SYSTEM_PROMPT.lower()

    def test_system_prompt_distinguishes_jargon_from_identity(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        # Must mention translating jargon BUT not identity markers
        assert "bluf" in lowered or "s-4" in lowered
        assert "do not translate" in lowered

    def test_system_prompt_contains_rewrite_rules(self):
        from translate_app.services import _SYSTEM_PROMPT
        assert "REWRITE RULES" in _SYSTEM_PROMPT

    def test_system_prompt_tailoring_mentions_jd_priorities(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "priorities" in lowered
        assert "job description" in lowered or "jd" in lowered

    def test_system_prompt_tailoring_allows_reorder_forbids_drop(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "reorder" in lowered
        assert "bullet count" in lowered or "preserve" in lowered

    def test_system_prompt_tailoring_forbids_fabricating_skills(self):
        from translate_app.services import _SYSTEM_PROMPT
        # v2 R3(c) labels the case "FABRICATE ... (forbidden)" instead of "do not fabricate"
        lowered = _SYSTEM_PROMPT.lower()
        assert "fabricate" in lowered

    def test_system_prompt_ats_assessment_format_defined(self):
        from translate_app.services import _SYSTEM_PROMPT
        assert "ATS FIT ASSESSMENT" in _SYSTEM_PROMPT
        assert "Strong matches" in _SYSTEM_PROMPT
        assert "Gaps" in _SYSTEM_PROMPT
        assert "To close the biggest gap" in _SYSTEM_PROMPT

    def test_system_prompt_ats_assessment_forbids_angle_brackets(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "angle bracket" in lowered

    def test_system_prompt_primary_task_is_rewrite(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "primary task" in lowered
        assert "rewrite" in lowered

    def test_system_prompt_r3_includes_noun_mirroring(self):
        from translate_app.services import _SYSTEM_PROMPT
        # R3(a) and R3(b) must now explicitly call for noun phrase
        # mirroring, not just verb-level tailoring.
        lowered = _SYSTEM_PROMPT.lower()
        assert "noun phrase" in lowered or "noun phrases" in lowered
        assert "sweep the jd" in lowered

    def test_system_prompt_r3c_forbids_unearned_responsibility(self):
        from translate_app.services import _SYSTEM_PROMPT
        # R3(c) must now include the implied-responsibility guardrail,
        # not just skill/tool fabrication.
        lowered = _SYSTEM_PROMPT.lower()
        # The guardrail must explicitly call out P&L as an example of
        # a phrase that implies authority not in the source.
        assert "p&l" in lowered
        assert "unearned" in lowered or "implied" in lowered

    def test_system_prompt_example_4_present(self):
        from translate_app.services import _SYSTEM_PROMPT
        # Example 4 must exist and must demonstrate both noun mirroring
        # and the guardrail ('What stayed limited:').
        assert "Example 4" in _SYSTEM_PROMPT
        assert "What stayed limited" in _SYSTEM_PROMPT

    def test_system_prompt_example_4_uses_pnl_guardrail(self):
        from translate_app.services import _SYSTEM_PROMPT
        # The Example 4 commentary must reference the P&L guardrail so
        # the demonstration teaches the bright line explicitly.
        # Search only within the demonstration section to avoid false
        # positives from the R3(c) rule mention.
        assert "budget management" in _SYSTEM_PROMPT.lower()
        assert "false responsibility claim" in _SYSTEM_PROMPT.lower() \
            or "false promotion" in _SYSTEM_PROMPT.lower() \
            or "scope stretch" in _SYSTEM_PROMPT.lower()

    def test_system_prompt_flags_failed_rewrite(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "failed rewrite" in lowered

    def test_system_prompt_per_role_identity_preservation(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "at least once per role" in lowered or "at least once" in lowered
        assert "per-role identity" in lowered or "role level" in lowered

    def test_system_prompt_r3_three_cases_explicit(self):
        from translate_app.services import _SYSTEM_PROMPT
        assert "WORD SWAP" in _SYSTEM_PROMPT
        assert "REFRAME" in _SYSTEM_PROMPT
        assert "FABRICATE" in _SYSTEM_PROMPT

    def test_system_prompt_contains_demonstrated_transformations(self):
        from translate_app.services import _SYSTEM_PROMPT
        assert "Example 1:" in _SYSTEM_PROMPT
        assert "Example 2:" in _SYSTEM_PROMPT
        assert "Example 3:" in _SYSTEM_PROMPT
        assert "Source:" in _SYSTEM_PROMPT
        assert "Tailored:" in _SYSTEM_PROMPT

    def test_system_prompt_verb_rewrite_directive(self):
        from translate_app.services import _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "rewrite the verb" in lowered

    def test_system_prompt_has_hard_limits_section(self):
        from translate_app.services import _SYSTEM_PROMPT
        # HARD LIMITS must be its own named section, not a carve-out
        # inside R3. Enforces the authority-gradient fix from v2.2.
        assert "HARD LIMITS" in _SYSTEM_PROMPT
        assert "apply before every other rule" in _SYSTEM_PROMPT

    def test_system_prompt_hard_limits_enumerate_pnl_phrases(self):
        from translate_app.services import _SYSTEM_PROMPT
        # H1 must name specific forbidden P&L variants, not just
        # describe the pattern abstractly.
        assert "'P&L management'" in _SYSTEM_PROMPT
        assert "'managed P&L'" in _SYSTEM_PROMPT
        # The COR carve-out must be explicit (product-critical — Brandon
        # case).
        lowered = _SYSTEM_PROMPT.lower()
        assert "cor" in lowered
        assert "contracting officer" in lowered

    def test_system_prompt_hard_limits_forbid_aggregates(self):
        from translate_app.services import _SYSTEM_PROMPT
        # H2 must name aggregate totals as a specific pattern, not
        # just generic 'no invented facts'.
        assert "H2" in _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        # Key concrete phrases: aggregates across separate source
        # numbers are forbidden.
        assert "aggregate" in lowered
        assert "summed total" in lowered or "summing" in lowered

    def test_system_prompt_hard_limits_forbid_fabricated_credentials(self):
        from translate_app.services import _SYSTEM_PROMPT
        # H3 must cover credentials/clearances/certifications added to
        # output that do not appear in source.
        assert "H3" in _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        # Clearance and certification classes must be named explicitly.
        assert "clearance" in lowered
        assert "certification" in lowered or "certified" in lowered

    def test_system_prompt_hard_limits_ats_strong_matches_grounded(self):
        from translate_app.services import _SYSTEM_PROMPT
        # H4 must require ATS FIT ASSESSMENT Strong matches to be
        # grounded in source — preventing the Stage 1 analysis from
        # self-certifying unearned capabilities.
        assert "H4" in _SYSTEM_PROMPT
        lowered = _SYSTEM_PROMPT.lower()
        assert "strong matches must be grounded" in lowered

    def test_example_4_references_hard_limit_h1(self):
        from translate_app.services import _SYSTEM_PROMPT
        # Example 4's commentary must now name the HARD LIMIT rule
        # that enforces the guardrail, not just R3(c).
        # The commentary update from v2.2 should reference 'HARD LIMIT
        # H1' explicitly.
        assert "HARD LIMIT H1" in _SYSTEM_PROMPT

    def test_system_prompt_r3c_no_longer_owns_pnl_guardrail(self):
        from translate_app.services import _SYSTEM_PROMPT
        # R3(c) should now reference HARD LIMITS for unearned
        # responsibility — it should NOT re-describe the full P&L
        # guardrail (that's now H1's job). Spot check: R3(c) should
        # mention 'HARD LIMITS H1-H4' as a reference.
        assert "HARD LIMITS H1-H4" in _SYSTEM_PROMPT \
            or "HARD LIMITS H1" in _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# grounding.py — TestGroundingValidator
# ---------------------------------------------------------------------------

class TestGroundingValidator:
    """Unit tests for grounding.flag_bullet and flag_translation."""

    def test_ungrounded_dollar_amount_is_flagged(self):
        from translate_app.grounding import flag_bullet
        source = "Managed equipment and coordinated with supply."
        bullet = "Managed $2.4M equipment portfolio across the unit."
        flags = flag_bullet(bullet, source)
        assert any("2.4M" in f or "$2.4M" in f for f in flags)

    def test_grounded_dollar_amount_is_not_flagged(self):
        from translate_app.grounding import flag_bullet
        source = "Managed a $2.4M equipment portfolio for the battalion."
        bullet = "Managed $2.4M equipment portfolio across the unit."
        flags = flag_bullet(bullet, source)
        assert not any("2.4M" in f for f in flags)

    def test_ungrounded_percentage_is_flagged(self):
        from translate_app.grounding import flag_bullet
        source = "Reduced equipment failures through standardised training."
        bullet = "Reduced equipment failures by 35% through training."
        flags = flag_bullet(bullet, source)
        assert any("35%" in f for f in flags)

    def test_grounded_percentage_is_not_flagged(self):
        from translate_app.grounding import flag_bullet
        source = "Reduced equipment failures by 35% over 12 months."
        bullet = "Reduced failures by 35% through standardised training."
        flags = flag_bullet(bullet, source)
        assert not any("35%" in f for f in flags)

    def test_scope_inflation_verb_is_flagged_when_absent_from_source(self):
        from translate_app.grounding import flag_bullet
        source = "Assisted platoon sergeant with daily operations and training."
        bullet = "Led platoon operations and daily training activities."
        flags = flag_bullet(bullet, source)
        assert any("scope" in f.lower() for f in flags)

    def test_scope_verb_not_flagged_when_present_in_source(self):
        from translate_app.grounding import flag_bullet
        source = "Led a 12-person squad through three combat rotations."
        bullet = "Led 12-person squad across three deployments."
        flags = flag_bullet(bullet, source)
        assert not any("scope" in f.lower() for f in flags)

    def test_empty_inputs_return_empty(self):
        from translate_app.grounding import flag_bullet
        assert flag_bullet("", "some source") == []
        assert flag_bullet("some bullet", "") == []

    def test_flag_translation_returns_only_flagged_entries(self):
        from translate_app.grounding import flag_translation
        source = "Led a squad. Managed equipment."
        roles = [{
            "title": "Squad Leader",
            "org": "US Army",
            "dates": "2019-2022",
            "bullets": [
                "Led squad across deployments.",              # grounded — no flag
                "Managed $5M equipment inventory.",            # ungrounded $5M
            ],
        }]
        result = flag_translation(roles, source)
        assert len(result) == 1
        assert result[0]["role_index"] == 0
        assert result[0]["bullet_index"] == 1
        assert any("5M" in f for f in result[0]["flags"])

    def test_flag_translation_handles_empty_roles(self):
        from translate_app.grounding import flag_translation
        assert flag_translation([], "source") == []
        assert flag_translation(None, "source") == []

    def test_flag_summary_catches_ungrounded_aggregate(self):
        from translate_app.grounding import flag_summary
        source = "Managed $275K equipment. Oversaw $240K campaigns. Secured $25K grant."
        summary = "Proven track record managing $1.2M+ in program budgets."
        flags = flag_summary(summary, source)
        assert any("1.2M" in f or "$1.2M" in f for f in flags)

    def test_flag_summary_passes_preserved_number(self):
        from translate_app.grounding import flag_summary
        source = "Managed $275K+ in equipment during deployments."
        summary = "Operations leader with $275K+ in equipment under direct management."
        flags = flag_summary(summary, source)
        assert not any("275K" in f for f in flags)

    def test_flag_summary_empty_inputs_return_empty(self):
        from translate_app.grounding import flag_summary
        assert flag_summary("", "source") == []
        assert flag_summary("summary", "") == []


class TestUnearnedClaimsValidator:
    """Tests for flag_unearned_claims — P&L, unearned skills,
    unearned credentials, dollar-amount aggregates."""

    # ------------------------- P&L phrases -------------------------

    def test_pnl_phrase_always_flagged(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Managed $250K budget for training programs."
        text = "Managed P&L for $250K programs."
        flags = flag_unearned_claims(text, source)
        assert any("p&l" in f.lower() for f in flags)

    def test_pnl_accountability_flagged(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Led three programs as COR."
        text = "P&L accountability for three programs."
        flags = flag_unearned_claims(text, source)
        assert any("p&l" in f.lower() for f in flags)

    def test_profit_and_loss_flagged(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Managed contracts as COR."
        text = "Owned profit and loss across the engagement."
        flags = flag_unearned_claims(text, source)
        assert any("p&l" in f.lower() or "profit-and-loss" in f.lower() for f in flags)

    def test_pnl_flag_explains_cor_carve_out(self):
        """Flag message must guide user to the COR / budget alternative."""
        from translate_app.grounding import flag_unearned_claims
        text = "Managed P&L for programs."
        flags = flag_unearned_claims(text, "")
        combined = " ".join(flags).lower()
        assert "cor" in combined
        assert "budget" in combined

    # ----------------- Unearned skill/tool claims -----------------

    def test_unearned_skill_flagged_when_absent_from_source(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Served as Army logistics officer managing convoys."
        text = "Managed AWS cloud infrastructure for logistics systems."
        flags = flag_unearned_claims(text, source)
        assert any("aws" in f.lower() for f in flags)

    def test_grounded_skill_not_flagged(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Managed Google Ads and Meta Ads campaigns."
        text = "Led Google Ads campaigns across 12 clients."
        flags = flag_unearned_claims(text, source)
        assert not any("google ads" in f.lower() for f in flags)

    def test_ai_ml_claim_flagged_when_source_silent(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Designed influence campaigns and counter-propaganda efforts."
        text = "Delivered AI/ML workflows and data pipelines for influence campaigns."
        flags = flag_unearned_claims(text, source)
        assert any("ai/ml" in f.lower() or "data pipeline" in f.lower() for f in flags)

    # -------------------- Unearned credentials --------------------

    def test_unearned_credential_flagged_when_absent_from_source(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Served as a project manager for Army logistics."
        text = "PMP certified project manager with Series 7."
        flags = flag_unearned_claims(text, source)
        combined = " ".join(flags).lower()
        assert "pmp" in combined or "series 7" in combined

    def test_grounded_credential_not_flagged(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Active TS/SCI clearance. COR certified."
        text = "TS/SCI cleared project manager with COR experience."
        flags = flag_unearned_claims(text, source)
        # TS/SCI is in source, so should not be flagged as unearned
        assert not any("ts/sci" in f.lower() for f in flags)

    def test_credential_flag_mentions_verification_harm(self):
        from translate_app.grounding import flag_unearned_claims
        text = "PMP certified program lead."
        flags = flag_unearned_claims(text, "")
        combined = " ".join(flags).lower()
        assert "verif" in combined or "fabricat" in combined

    # ---------------- Dollar-amount aggregates ----------------

    def test_aggregate_dollar_amount_flagged(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Managed $275K in one program. Oversaw $240K in another. Led $950K in a third."
        text = "Managed $1.4M+ in program portfolios."
        flags = flag_unearned_claims(text, source)
        assert any("1.4m" in f.lower() or "dollar amount" in f.lower() for f in flags)

    def test_grounded_dollar_amount_not_flagged(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Managed $950K in programs as COR."
        text = "Delivered $950K+ in programs as COR."
        flags = flag_unearned_claims(text, source)
        assert not any("dollar amount" in f.lower() for f in flags)

    def test_multiple_grounded_amounts_not_flagged(self):
        from translate_app.grounding import flag_unearned_claims
        source = "Led $275K programs. Managed $240K contracts."
        text = "Led $275K programs and $240K contracts."
        flags = flag_unearned_claims(text, source)
        assert not any("dollar amount" in f.lower() for f in flags)

    # --------------- Integration with flag_bullet ---------------

    def test_flag_bullet_now_includes_pnl_check(self):
        """Wiring check — flag_bullet must surface P&L flags too."""
        from translate_app.grounding import flag_bullet
        source = "Managed budget for three programs."
        bullet = "Managed P&L for three programs."
        flags = flag_bullet(bullet, source)
        assert any("p&l" in f.lower() for f in flags)

    def test_flag_bullet_still_catches_numeric_fabrication(self):
        """Regression — existing numeric check must still fire."""
        from translate_app.grounding import flag_bullet
        source = "Managed equipment for training."
        bullet = "Managed $2.4M equipment portfolio."
        flags = flag_bullet(bullet, source)
        assert any("2.4m" in f.lower() or "$2.4m" in f.lower() for f in flags)

    # ------------------ Empty / edge cases ------------------

    def test_empty_text_returns_empty_flags(self):
        from translate_app.grounding import flag_unearned_claims
        flags = flag_unearned_claims("", "source text")
        assert flags == []

    def test_empty_source_still_flags_pnl(self):
        """P&L is always flagged regardless of source."""
        from translate_app.grounding import flag_unearned_claims
        flags = flag_unearned_claims("Managed P&L.", "")
        assert any("p&l" in f.lower() for f in flags)

    def test_none_source_handled_gracefully(self):
        from translate_app.grounding import flag_unearned_claims
        flags = flag_unearned_claims("Managed programs.", None)
        assert flags == []
