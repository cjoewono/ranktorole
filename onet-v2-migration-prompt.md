# O*NET v2 API Migration — X-API-Key Authentication

## Context

O*NET API key has been approved and added to `.env` as `ONET_API_KEY`. All three O*NET views currently hit the public `https://services.onetcenter.org/ws` base URL with no auth. We need to migrate to the authenticated v2 API at `https://api-v2.onetcenter.org` using an `X-API-Key` header.

## Rules

- Read every file listed before writing any code
- Run `cd /app && python -m pytest -x -q` FIRST. Record the count as BASELINE (expect 108)
- All changes must maintain BASELINE test count — run pytest after every task
- Do NOT modify URLs, frontend files, or doc files
- Do NOT touch `onet_app/urls.py` — routes stay the same

## Files to read first

- `backend/onet_app/views.py`
- `backend/onet_app/tests.py`
- `backend/config/settings.py`
- `.env`
- `CLAUDE.md`

---

## Task 1 — Add ONET_API_KEY to Django settings

File: `backend/config/settings.py`

Add this line near the other env-based settings (near `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID`, etc.):

```python
ONET_API_KEY = os.environ.get('ONET_API_KEY', '')
```

Run pytest — expect BASELINE.

---

## Task 2 — Migrate onet_app/views.py

File: `backend/onet_app/views.py`

### 2a — Update imports and module-level constants

Add `from django.conf import settings` to the imports.

Replace:
```python
ONET_BASE = "https://services.onetcenter.org/ws"
```

With:
```python
ONET_BASE = "https://api-v2.onetcenter.org"

def _onet_headers():
    """Shared headers for all O*NET v2 API requests."""
    return {
        "Accept": "application/json",
        "X-API-Key": settings.ONET_API_KEY,
    }
```

### 2b — Update OnetSearchView

In `OnetSearchView.get()`, find every `http_requests.get()` call and replace `headers={"Accept": "application/json"}` with `headers=_onet_headers()`.

Also update the endpoint paths. The v2 API uses different routes than the ws API:
- Search: `{ONET_BASE}/mnm/search` → `{ONET_BASE}/mnm/search` (same path, different base)
- Skills: `{ONET_BASE}/online/occupations/{code}/summary/skills` → `{ONET_BASE}/online/occupations/{code}/summary/skills` (same path, different base)

So only the headers change for `OnetSearchView`. Replace every `headers={"Accept": "application/json"}` with `headers=_onet_headers()`.

### 2c — Update OnetMilitarySearchView

In `OnetMilitarySearchView.get()`:
- Replace `headers={"Accept": "application/json"}` with `headers=_onet_headers()`
- The endpoint path `{ONET_BASE}/veterans/military/` stays the same structurally (just base URL changed)

### 2d — Update OnetCareerDetailView

In `OnetCareerDetailView`:
- Update `_fetch_json()` to use the shared headers. Replace:
  ```python
  headers={"Accept": "application/json"},
  ```
  With:
  ```python
  headers=_onet_headers(),
  ```
- The career detail paths `{ONET_BASE}/veterans/careers/{onet_code}/...` stay the same structurally

Run pytest — expect BASELINE.

---

## Task 3 — Update test mocks

File: `backend/onet_app/tests.py`

The existing tests mock `onet_app.views.http_requests.get` which still works. However, we should add one test to verify the API key header is being sent.

Add this test to `TestOnetSearchView`:

```python
    def test_api_key_header_sent(self, auth_client):
        """Verify X-API-Key header is included in outbound O*NET requests."""
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"career": []}
            mock_get.return_value = mock_resp

            with patch("onet_app.views.settings") as mock_settings:
                mock_settings.ONET_API_KEY = "test-key-123"
                auth_client.get("/api/v1/onet/search/?keyword=medic")

            # Verify the header was passed
            call_args = mock_get.call_args
            assert call_args is not None
            headers = call_args[1].get("headers", {})
            assert "X-API-Key" in headers
```

Add this test to `TestOnetMilitarySearchView`:

```python
    def test_api_key_header_sent(self, auth_client):
        """Verify X-API-Key header is included in military search requests."""
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"career": [], "military_matches": {}}
            mock_get.return_value = mock_resp

            with patch("onet_app.views.settings") as mock_settings:
                mock_settings.ONET_API_KEY = "test-key-456"
                auth_client.get("/api/v1/onet/military/?keyword=11B")

            call_args = mock_get.call_args
            assert call_args is not None
            headers = call_args[1].get("headers", {})
            assert "X-API-Key" in headers
```

Add this test to `TestOnetCareerDetailView`:

```python
    def test_api_key_header_sent(self, auth_client):
        """Verify X-API-Key header is included in career detail requests."""
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"title": "Test", "description": "Test", "tags": {}}
            mock_get.return_value = mock_resp

            with patch("onet_app.views.settings") as mock_settings:
                mock_settings.ONET_API_KEY = "test-key-789"
                auth_client.get("/api/v1/onet/career/47-2061.00/")

            call_args = mock_get.call_args
            assert call_args is not None
            headers = call_args[1].get("headers", {})
            assert "X-API-Key" in headers
```

Run pytest — expect BASELINE + 3.

---

## Task 4 — Verify .env has the key

Check that `.env` contains `ONET_API_KEY=...` (non-empty value). If it does NOT exist, stop and report — do not create or modify `.env`.

Check that `.env.example` documents the variable. If `ONET_API_KEY` is not listed there, add it:

```
ONET_API_KEY=your-onet-api-key-here
```

---

## Task 5 — Doc updates

### CLAUDE.md

Find the O*NET section and update:
- Note that O*NET now uses authenticated v2 API (`https://api-v2.onetcenter.org`)
- Auth via `X-API-Key` header (key from `ONET_API_KEY` env var)
- Remove any references to the old public `services.onetcenter.org/ws` URL

### ARCHITECTURE.md

In the Career Recon section, add a note:
- O*NET v2 API with `X-API-Key` auth (env: `ONET_API_KEY`)

### SECURITY.md

If there's a secrets/env vars section, add `ONET_API_KEY` to the list of required secrets.

### PROJECTLOG.md

Add a session entry at the bottom:

```markdown
---

## April 13, 2026 | O*NET v2 API Migration

**Status:** ✅ Complete

### Summary

Migrated all three O*NET proxy views from the public `services.onetcenter.org/ws` endpoint to the authenticated v2 API at `api-v2.onetcenter.org`. Auth uses `X-API-Key` header sourced from `ONET_API_KEY` env var. No endpoint path changes — all routes and response shapes unchanged.

### Changes

| File | Action | Detail |
|------|--------|--------|
| `config/settings.py` | Modified | Added `ONET_API_KEY` from env |
| `onet_app/views.py` | Modified | New base URL, shared `_onet_headers()` helper, all requests now send `X-API-Key` |
| `onet_app/tests.py` | Modified | Added 3 tests verifying API key header is sent |
| `.env.example` | Modified | Added `ONET_API_KEY` |
| Docs | Modified | CLAUDE.md, ARCHITECTURE.md, SECURITY.md, PROJECTLOG.md updated |
```

---

## Commit

```bash
git add -A
git commit -m "feat: migrate O*NET to v2 API with X-API-Key auth

- Base URL: services.onetcenter.org/ws → api-v2.onetcenter.org
- Shared _onet_headers() sends X-API-Key on all requests
- ONET_API_KEY added to settings.py + .env.example
- 3 new tests verify header presence
- All docs updated"
```

## Report

1. BASELINE test count
2. Final test count (expect BASELINE + 3)
3. List of files modified
4. Confirm `.env` has `ONET_API_KEY` set (yes/no, do NOT print the key)
