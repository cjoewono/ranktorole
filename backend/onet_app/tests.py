"""Tests for onet_app shared utilities.

After the Recon rebuild (April 2026), the view-layer tests (OnetSearchView,
OnetMilitarySearchView, OnetCareerDetailView, ReconEnrichView) were removed
along with their endpoints. Remaining tests cover the shared helpers that
recon_app continues to rely on:

- _resolve_mos_title()                 — canonical MOS title resolver
- _check_and_increment_global_ceiling  — atomic daily spend ceiling
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGlobalCeiling:
    """Atomic daily spend ceiling for Haiku calls."""

    def test_exceeds_ceiling_returns_false(self, db, settings):
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _check_and_increment_global_ceiling

        cache.clear()
        settings.RECON_ENRICH_DAILY_CEILING = 2

        assert _check_and_increment_global_ceiling() is True   # count=1
        assert _check_and_increment_global_ceiling() is True   # count=2
        assert _check_and_increment_global_ceiling() is False  # count=3 > ceiling

        cache.clear()


class TestResolveMosTitle:
    """Tests for the MOS title resolver (O*NET veterans/military lookup)."""

    def test_returns_title_on_exact_match(self, db):
        """Successful O*NET response with matching code returns title."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "11B", "title": "Infantryman (Army - Enlisted)", "branch": "army"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Army", "11B")
            assert title == "Infantryman (Army - Enlisted)"

        cache.clear()

    def test_returns_empty_on_no_match(self, db):
        """O*NET returns matches but none are exact code — empty string."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "99Z", "title": "Something Else", "branch": "army"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Army", "11B")
            assert title == ""

        cache.clear()

    def test_returns_cached_result_on_second_call(self, db):
        """Second call with same (branch, mos) hits cache, not O*NET."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "11B", "title": "Infantryman (Army - Enlisted)", "branch": "army"},
                ],
            }
            mock_get.return_value = mock_resp

            t1 = _resolve_mos_title("Army", "11B")
            t2 = _resolve_mos_title("Army", "11B")

            assert t1 == "Infantryman (Army - Enlisted)"
            assert t2 == t1
            assert mock_get.call_count == 1  # Second call cached

        cache.clear()

    def test_navy_officer_designator_uses_local_lookup(self, db):
        """Navy 1110 resolves via local dict without hitting O*NET."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            title = _resolve_mos_title("Navy", "1110")

        assert title == "Surface Warfare Officer (Navy - Officer)"
        # O*NET should not have been called — local dict hit
        assert mock_get.call_count == 0

        cache.clear()

    def test_navy_enlisted_falls_back_to_onet(self, db):
        """Navy IT (enlisted) isn't in local dict — should hit O*NET."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "IT", "title": "Information Systems Technician (Navy - Enlisted)", "branch": "navy"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Navy", "IT")

        assert title == "Information Systems Technician (Navy - Enlisted)"
        assert mock_get.call_count == 1  # Did hit O*NET

        cache.clear()

    def test_coast_guard_rating_uses_local_lookup(self, db):
        """CG BM (Boatswain's Mate) resolves via local dict, no O*NET call."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            title = _resolve_mos_title("Coast_Guard", "BM")

        assert title == "Boatswain's Mate (Coast Guard - Enlisted)"
        assert mock_get.call_count == 0

        cache.clear()

    def test_coast_guard_unknown_rating_returns_empty(self, db):
        """CG rating not in dict falls through — O*NET returns empty → empty."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"military_match": []}
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Coast_Guard", "ZZ")

        assert title == ""

        cache.clear()

    def test_air_force_prefix_match_strips_sub_specialty(self, db):
        """AF 11F user input matches O*NET's 11F1B, returns generic title."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "11F1B", "title": "Fighter Pilot, A-10 (Air Force - Commissioned Officer only)"},
                    {"code": "11F1C", "title": "Fighter Pilot, F-15 (Air Force - Commissioned Officer only)"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Air_Force", "11F")

        assert title == "Fighter Pilot (Air Force - Commissioned Officer only)"

        cache.clear()

    def test_af_exact_match_wins_over_prefix(self, db):
        """When O*NET returns exact code match, prefix-match doesn't run."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "21A1", "title": "Aircraft Maintenance Sub-specialty (Air Force - Commissioned Officer only)"},
                    {"code": "21A", "title": "Aircraft Maintenance (Air Force - Commissioned Officer only)"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Air_Force", "21A")

        assert title == "Aircraft Maintenance (Air Force - Commissioned Officer only)"

        cache.clear()

    def test_army_unchanged_behavior(self, db):
        """Army uses O*NET exact match — verify no regression from new code paths."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "11B", "title": "Infantryman (Army - Enlisted)"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Army", "11B")

        assert title == "Infantryman (Army - Enlisted)"

        cache.clear()
