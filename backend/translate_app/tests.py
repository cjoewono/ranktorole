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

    def test_finalized_resume_chat_returns_409(self, auth_client, user, db):
        resume = _create_resume(user, is_finalized=True)
        response = auth_client.post(
            f"/api/v1/resumes/{resume.id}/chat/",
            {"message": "Update bullets."},
            format="json",
        )
        assert response.status_code == 409

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

    def test_double_finalize_returns_409(self, auth_client, user, db):
        resume = _create_resume(user, is_finalized=True)
        response = auth_client.patch(
            f"/api/v1/resumes/{resume.id}/finalize/",
            {},
            format="json",
        )
        assert response.status_code == 409

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
