"""
Tests for recon_app brainstorm endpoint.

Mocks at the recon_app.services level — root conftest handles SDK-level safety.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient

from recon_app.schemas import BrainstormCandidate, BrainstormRanking


BRAINSTORM_URL = "/api/v1/recon/brainstorm/"

VALID_PAYLOAD = {
    "services": [{"branch": "Army", "mos_code": "11B"}],
    "grade": "E-6",
    "position": "Squad Leader",
    "target_career_field": "Cybersecurity",
    "education": ["Bachelor's in Computer Science"],
    "certifications": ["CompTIA Security+"],
    "licenses": [],
    "state": "Washington",
}

FAKE_BASELINE = [
    {"code": "15-1212.00", "title": "Information Security Analysts", "match_type": "most_duties", "tags": {}},
    {"code": "15-1299.04", "title": "Penetration Testers", "match_type": "some_duties", "tags": {}},
    {"code": "15-1241.00", "title": "Computer Network Architects", "match_type": "keyword", "tags": {}},
]

FAKE_DETAIL = {
    "code": "15-1212.00",
    "title": "Information Security Analysts",
    "description": "Protect computer networks.",
    "tags": {"bright_outlook": True},
    "skills": [{"name": "Risk Management", "description": ""}],
    "knowledge": [{"name": "Computers and Electronics", "description": ""}],
    "technology": [],
    "outlook": {
        "category": "Bright",
        "description": "Growing field.",
        "salary": {"annual_median": "102600", "annual_10th": "60060", "annual_90th": "165920"},
    },
}


def _fake_ranking(code_a, code_b, code_c):
    return BrainstormRanking(candidates=[
        BrainstormCandidate(
            onet_code=code_a, match_score=85,
            match_rationale="Strong fit based on Security+ cert.",
            skill_gaps=["OSHA 30"],
            transferable_skills=["Leadership", "Logistics", "Risk"],
        ),
        BrainstormCandidate(
            onet_code=code_b, match_score=72,
            match_rationale="Good fit.",
            skill_gaps=["PMP"],
            transferable_skills=["Planning", "Ops"],
        ),
        BrainstormCandidate(
            onet_code=code_c, match_score=60,
            match_rationale="Adjacent role.",
            skill_gaps=["Cert X"],
            transferable_skills=["Training"],
        ),
    ])


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def auth_client(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="testvet", email="testvet@example.com", password="testpass123"
    )
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_unauthenticated_returns_401(client):
    resp = client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Payload validation tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_empty_services_returns_400(auth_client):
    payload = {**VALID_PAYLOAD, "services": []}
    resp = auth_client.post(BRAINSTORM_URL, data=payload, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_missing_services_returns_400(auth_client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "services"}
    resp = auth_client.post(BRAINSTORM_URL, data=payload, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_blank_branch_returns_400(auth_client):
    payload = {**VALID_PAYLOAD, "services": [{"branch": "", "mos_code": "11B"}]}
    resp = auth_client.post(BRAINSTORM_URL, data=payload, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_invalid_branch_returns_400(auth_client):
    payload = {**VALID_PAYLOAD, "services": [{"branch": "Klingon Defense Force", "mos_code": "11B"}]}
    resp = auth_client.post(BRAINSTORM_URL, data=payload, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_blank_mos_code_returns_400(auth_client):
    payload = {**VALID_PAYLOAD, "services": [{"branch": "Army", "mos_code": ""}]}
    resp = auth_client.post(BRAINSTORM_URL, data=payload, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_happy_path_returns_best_match_and_two_runners_up(auth_client):
    detail = {**FAKE_DETAIL}
    ranking = _fake_ranking("15-1212.00", "15-1299.04", "15-1241.00")

    with patch("recon_app.services._build_merged_baseline", return_value=FAKE_BASELINE), \
         patch("recon_app.services._call_haiku_typed", return_value=ranking), \
         patch("recon_app.services._fetch_full_detail", return_value={**detail}), \
         patch("recon_app.services._check_and_increment_global_ceiling", return_value=True):

        resp = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert "best_match" in data
    assert data["best_match"]["reasoning"]["match_score"] == 85
    assert len(data["also_consider"]) == 2
    assert data["also_consider"][0]["code"] == "15-1299.04"
    assert data["also_consider"][1]["code"] == "15-1241.00"
    assert data["degraded"] is False


# ---------------------------------------------------------------------------
# Degraded fallbacks
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_haiku_failure_returns_degraded_200(auth_client):
    detail = {**FAKE_DETAIL}

    with patch("recon_app.services._build_merged_baseline", return_value=FAKE_BASELINE), \
         patch("recon_app.services._call_haiku_typed", side_effect=ValueError("Haiku exploded")), \
         patch("recon_app.services._fetch_full_detail", return_value={**detail}), \
         patch("recon_app.services._check_and_increment_global_ceiling", return_value=True):

        resp = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["degraded"] is True
    assert data["best_match"]["reasoning"] is None
    assert data["also_consider"] == []


@pytest.mark.django_db
def test_haiku_picks_all_invalid_codes_returns_degraded_200(auth_client):
    # Haiku returns codes that are NOT in the baseline
    bad_ranking = BrainstormRanking(candidates=[
        BrainstormCandidate(
            onet_code="99-9999.99", match_score=90,
            match_rationale="Hallucinated.",
            skill_gaps=[],
            transferable_skills=[],
        ),
    ])
    detail = {**FAKE_DETAIL}

    with patch("recon_app.services._build_merged_baseline", return_value=FAKE_BASELINE), \
         patch("recon_app.services._call_haiku_typed", return_value=bad_ranking), \
         patch("recon_app.services._fetch_full_detail", return_value={**detail}), \
         patch("recon_app.services._check_and_increment_global_ceiling", return_value=True):

        resp = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")

    assert resp.status_code == 200
    assert resp.json()["degraded"] is True


@pytest.mark.django_db
def test_empty_baseline_returns_502(auth_client):
    with patch("recon_app.services._build_merged_baseline", return_value=[]):
        resp = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")

    assert resp.status_code == 502


@pytest.mark.django_db
def test_ceiling_hit_returns_degraded_with_onet_only(auth_client):
    detail = {**FAKE_DETAIL}

    with patch("recon_app.services._build_merged_baseline", return_value=FAKE_BASELINE), \
         patch("recon_app.services._check_and_increment_global_ceiling", return_value=False), \
         patch("recon_app.services._fetch_full_detail", return_value={**detail}):

        resp = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")

    assert resp.status_code == 200
    data = resp.json()
    assert data["degraded"] is True
    assert data["best_match"]["reasoning"] is None


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_cache_hit_skips_onet_and_haiku_calls(auth_client):
    detail = {**FAKE_DETAIL}
    ranking = _fake_ranking("15-1212.00", "15-1299.04", "15-1241.00")

    build_mock = MagicMock(return_value=FAKE_BASELINE)
    haiku_mock = MagicMock(return_value=ranking)
    detail_mock = MagicMock(return_value={**detail})
    ceiling_mock = MagicMock(return_value=True)

    with patch("recon_app.services._build_merged_baseline", build_mock), \
         patch("recon_app.services._call_haiku_typed", haiku_mock), \
         patch("recon_app.services._fetch_full_detail", detail_mock), \
         patch("recon_app.services._check_and_increment_global_ceiling", ceiling_mock):

        resp1 = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")
        resp2 = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    # Second call must have been served from cache
    assert build_mock.call_count == 1
    assert haiku_mock.call_count == 1


@pytest.mark.django_db
def test_different_form_gets_different_cache_key(auth_client):
    from recon_app.services import _cache_key

    form_a = {
        "services": [{"branch": "Army", "mos_code": "11B"}],
        "grade": "E-5", "position": "", "target_career_field": "",
        "education": [], "certifications": [], "licenses": [], "state": "",
    }
    form_b = {
        "services": [{"branch": "Navy", "mos_code": "IT"}],
        "grade": "E-5", "position": "", "target_career_field": "",
        "education": [], "certifications": [], "licenses": [], "state": "",
    }
    assert _cache_key(form_a) != _cache_key(form_b)


# ---------------------------------------------------------------------------
# Multi-service merge / dedupe
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_multiple_services_merge_and_dedupe_baseline(auth_client):
    """Two service entries that share a code — keep the stronger match_type."""
    from recon_app.services import _build_merged_baseline

    branch_a_results = [
        {"code": "15-1212.00", "title": "InfoSec Analyst", "match_type": "keyword", "tags": {}},
        {"code": "15-1299.04", "title": "Pen Tester", "match_type": "some_duties", "tags": {}},
    ]
    branch_b_results = [
        {"code": "15-1212.00", "title": "InfoSec Analyst", "match_type": "most_duties", "tags": {}},
        {"code": "15-1241.00", "title": "Net Architect", "match_type": "keyword", "tags": {}},
    ]

    def _fake_fetch(branch, mos_code):
        if branch == "Army":
            return branch_a_results
        return branch_b_results

    form = {
        "services": [
            {"branch": "Army", "mos_code": "11B"},
            {"branch": "Navy", "mos_code": "IT"},
        ],
        "grade": "", "position": "", "target_career_field": "",
        "education": [], "certifications": [], "licenses": [], "state": "",
    }

    with patch("recon_app.services._fetch_baseline_for_service", side_effect=_fake_fetch):
        merged = _build_merged_baseline(form)

    codes = [c["code"] for c in merged]
    assert len(codes) == 3  # 3 unique codes
    assert len(set(codes)) == 3  # all unique

    # 15-1212.00 must keep "most_duties" (stronger from branch_b)
    entry_1212 = next(c for c in merged if c["code"] == "15-1212.00")
    assert entry_1212["match_type"] == "most_duties"


# ---------------------------------------------------------------------------
# Invalid code filtering
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_onet_code_validation_rejects_bad_codes_returns_degraded(auth_client):
    bad_ranking = BrainstormRanking(candidates=[
        BrainstormCandidate(
            onet_code="99-9999.99",  # Not in baseline
            match_score=80,
            match_rationale="Invented code.",
            skill_gaps=[],
            transferable_skills=[],
        ),
    ])
    detail = {**FAKE_DETAIL}

    with patch("recon_app.services._build_merged_baseline", return_value=FAKE_BASELINE), \
         patch("recon_app.services._call_haiku_typed", return_value=bad_ranking), \
         patch("recon_app.services._fetch_full_detail", return_value={**detail}), \
         patch("recon_app.services._check_and_increment_global_ceiling", return_value=True):

        resp = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")

    assert resp.status_code == 200
    assert resp.json()["degraded"] is True


# ---------------------------------------------------------------------------
# strip_tags defense
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_strip_tags_applied_to_reasoning_strings(auth_client):
    detail = {**FAKE_DETAIL}
    xss_ranking = BrainstormRanking(candidates=[
        BrainstormCandidate(
            onet_code="15-1212.00",
            match_score=85,
            match_rationale="<script>alert('xss')</script>Strong fit.",
            skill_gaps=["<b>OSHA 30</b>"],
            transferable_skills=["<em>Leadership</em>"],
        ),
        BrainstormCandidate(
            onet_code="15-1299.04",
            match_score=70,
            match_rationale="<img src=x onerror=alert(1)>Good fit.",
            skill_gaps=[],
            transferable_skills=[],
        ),
    ])

    with patch("recon_app.services._build_merged_baseline", return_value=FAKE_BASELINE), \
         patch("recon_app.services._call_haiku_typed", return_value=xss_ranking), \
         patch("recon_app.services._fetch_full_detail", return_value={**detail}), \
         patch("recon_app.services._check_and_increment_global_ceiling", return_value=True):

        resp = auth_client.post(BRAINSTORM_URL, data=VALID_PAYLOAD, format="json")

    assert resp.status_code == 200
    data = resp.json()
    rationale = data["best_match"]["reasoning"]["match_rationale"]
    assert "<script>" not in rationale
    assert "Strong fit." in rationale

    skill_gaps = data["best_match"]["reasoning"]["skill_gaps"]
    assert "<b>" not in skill_gaps[0]
    assert "OSHA 30" in skill_gaps[0]

    also_rationale = data["also_consider"][0]["match_rationale"]
    assert "<img" not in also_rationale
    assert "Good fit." in also_rationale
