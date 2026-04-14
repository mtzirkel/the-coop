# The Coop — Project Scope

A community co-op tracker for a small neighborhood near East Glacier Park, Montana.
Track work hours, manage wood inventory, and split profits at year-end.

## What It Does

| Feature | Status | Who sees it |
|---------|--------|-------------|
| **Dashboard** — weekly stats, YTD financials, recent entries | Done | Everyone |
| **Log Hours** — start/end time, job, location, notes | Done | Everyone |
| **My Hours** — personal time entries with period filters | Done | Everyone |
| **Team Hours** — all members' entries with filters | Done | Admin only |
| **Approvals** — approve/reject pending entries (fade-out animation) | Done | Approvers + Admin |
| **Wood Inventory** — available, spoken for, sold with status filters | Done | Everyone |
| **Finances** — income, expenses, net profit, member splits | Done | Admin only |
| **Dark/Light Mode** — toggle in nav, persists across sessions | Done | Everyone |
| **Offline Support** — cached pages, queued writes, auto-sync | Done | Everyone |

## Roles

| Role | Can do | Needs approver? |
|------|--------|-----------------|
| **Admin** | Everything — see all entries, approve anyone, manage finances | No |
| **Member** | Log hours (auto-approved), see inventory, approve their kids | No |
| **Minor** | Log hours (pending approval), see inventory | Yes |

## Tech Stack

- **Backend:** Django 5 + Django Ninja (REST API) + HTMX
- **Frontend:** Svelte 5 "islands" mounted into Django templates via Vite
- **Styling:** Tailwind CSS v4, OKLCH colors, 37signals-inspired design
- **Auth:** noegos-auth (separate SvelteKit service) — JWT cookie, TOTP login
- **Database:** SQLite (dev), PostgreSQL (production)
- **PWA:** Service worker with offline cache + write queue

## Data Model

```
CoopMember (role: admin|member|minor, approver → CoopMember)
    ↓
TimeEntry (job, date, time_start, time_end, hours, location, status)
    ↓ approved_by
CoopMember

Job (name, description, rate_multiplier)
WoodInventory (wood_type, quantity, status, buyer, location)
Income (date, amount, source)
Expense (date, amount, category)
```

## Running Locally

```bash
# First time
cd ~/Projects/the-coop
uv sync                          # install Python deps
cd frontend && npm install       # install JS deps
cd ..
uv run python manage.py migrate  # create database
uv run python manage.py seed     # load sample data

# Development
./bin/dev                        # starts Django :8000 + Vite :5176

# Tests
uv run python manage.py test coop -v2
uv run python bin/audit-tests
```

Dev mode auto-logs you in as admin (no auth service needed).

## Deployment Plan

**Target:** Linode instance (badger) — already running other apps.

```
noegosunderwater.com
├── auth.noegosunderwater.com  → noegos-auth (SvelteKit/Node)
├── coop.noegosunderwater.com  → The Coop (Django/Gunicorn)
├── chat.noegosunderwater.com  → Campfire (future)
└── board.noegosunderwater.com → Fizzy (future)
```

- Postgres standalone on the box (not in Docker)
- Nginx reverse proxy + Let's Encrypt SSL
- DNS at Namecheap
- Cookie domain `.noegosunderwater.com` covers all subdomains

## What's Next

1. **Deploy** auth + coop to badger (survey existing setup first)
2. **Income/expense forms** in the web UI (currently admin panel + API only)
3. **Campfire + Fizzy** bolt-ons for team chat and task planning
4. **PWA icons** for install-to-homescreen
5. **Push notifications** for approval alerts (parents get notified when kids log hours)
