# RankToRole

**Military-to-civilian resume translation, powered by Claude.**

RankToRole turns a veteran's service record into a targeted civilian resume.
Upload a PDF, paste a job description, and the app produces a role-grouped
draft plus a short refinement chat — all grounded in O\*NET career data.

**Live:** [cjoewono.com](https://cjoewono.com) *(pending final deployment)*
**Deadline:** April 24, 2026

---

## Features

- **PDF upload** — PyMuPDF extracts text from service records (no OCR, no file bytes stored)
- **Targeted draft** — single Claude call returns a role-grouped resume plus one JD-specific clarifying question
- **Refinement chat** — stateful, DB-backed conversation that updates the draft in place
- **Inline editing** — live redline diff vs. the initial AI draft, per-bullet AI suggestions with Accept / Dismiss
- **PDF export** — role-grouped clean format via jsPDF, downloads to the user's machine
- **Career Recon** — standalone O\*NET career explorer at `/recon` (MOS code → civilian matches, salary, outlook)
- **Free / Pro tiers** — Stripe-powered subscription with Customer Portal, tiered rate limits, immutable audit log
- **Google OAuth** — passwordless sign-in alongside email + password

---

## Stack

| Layer        | Technology                                                         |
| ------------ | ------------------------------------------------------------------ |
| Frontend     | React 18 (Vite) · Tailwind CSS · React Router DOM · jsPDF           |
| Backend      | Django 4.2 · Django REST Framework · SimpleJWT                     |
| Database     | PostgreSQL 16 (named volume)                                       |
| AI           | Claude API (`claude-sonnet-4-20250514`) via `anthropic` Python SDK  |
| Billing      | Stripe Checkout + Customer Portal + Webhooks                       |
| Auth         | JWT (hybrid: access in memory, refresh in httpOnly cookie) + Google OAuth |
| External API | O\*NET v2 (`api-v2.onetcenter.org`, `X-API-Key` auth)               |
| Infra        | Docker Compose · Nginx · AWS EC2 · Let's Encrypt                   |

---

## Quick Start (Dev)

Requires Docker Desktop and Node 20+.

```bash
git clone https://github.com/cjoewono/ranktorole.git
cd ranktorole
cp .env.example .env          # fill in the secrets listed below
docker compose up --build     # starts db + backend in Docker
cd frontend && npm install && npm run dev   # Vite on host with HMR
```

Open `http://localhost:5173`. Vite proxies `/api/` to `localhost:8000`.

### Required environment variables

See `.env.example` for the full list. Minimum to boot:

```
SECRET_KEY=...                    # ≥32 bytes, secrets.token_urlsafe(64)
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:5173/auth/google/callback
ONET_API_KEY=...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

### Common commands

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend pytest            # backend test suite (116 passing)
docker compose exec frontend npm run build    # production bundle
```

---

## Architecture at a glance

```
PDF upload ─► PyMuPDF ─► Resume.military_text (text only; bytes discarded)
                           │
JD paste ─────────────────┴─► Claude call 1 ─► draft + clarifying_question
                                 │                  │
                                 ▼                  ▼
                       session_anchor           left pane: draft
                       (compressed, ~350 tok)   right pane: chat bubble
                                 │
User chats ────► session_anchor + chat_history (DB) + message ─► Claude call 2..N
                                 │
                                 ▼
                       updated draft + assistant_reply
                                 │
User finalizes ─► PATCH /finalize/ ─► is_finalized=True ─► PDF export
```

**Key rule:** raw `military_text` and `job_description` are sent to Claude
exactly once (call 1). Every refinement turn works from the compressed
`session_anchor` plus DB-backed `chat_history`, keeping each call under
~1,350 input tokens.

For the full design, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Project Docs

| File                                 | Purpose                                               |
| ------------------------------------ | ----------------------------------------------------- |
| [ARCHITECTURE.md](ARCHITECTURE.md)   | System design, product flow, context window strategy  |
| [DATA_CONTRACT.md](DATA_CONTRACT.md) | Every endpoint's input, output, and error shapes      |
| [SECURITY.md](SECURITY.md)           | Secrets, auth, input validation, PCI scope, HTTPS     |
| [CLAUDE.md](CLAUDE.md)               | Rules for AI coding assistants working on the repo    |
| [TASKS.md](TASKS.md)                 | Current sprint status and completed work              |
| [PROJECTLOG.md](PROJECTLOG.md)       | Session-by-session build log                          |

---

## Production Deployment

Single EC2 host, Docker Compose, Let's Encrypt for TLS, Nginx as the only
public-facing service (ports 80 and 443).

See [SECURITY.md](SECURITY.md) § HTTPS / SSL and
[ARCHITECTURE.md](ARCHITECTURE.md) § SSL / HTTPS (Production) for the full
deploy procedure.

---

## License

Private — capstone project, not yet licensed for external use.

**Reference implementation:** [BridgeBoard](https://github.com/cjoewono/bridgeboard)