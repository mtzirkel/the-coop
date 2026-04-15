# The Coop — Project Scope

A community co-op tracker for a small neighborhood near East Glacier Park, Montana.
Track work hours, manage wood inventory, and split profits at year-end.

**Live at:** https://coop.noegosunderwater.com
**Sign-in guide for new users:** [SIGNIN.md](SIGNIN.md)
**Recent changes:** [CHANGELOG.md](CHANGELOG.md)

## What It Does

| Feature | Status | Who sees it |
|---------|--------|-------------|
| **Dashboard** — weekly stats, YTD financials, recent entries | ✅ Done | Everyone |
| **Log Hours** — start/end time, job, location, notes | ✅ Done | Everyone |
| **Inline job creation** — add a new job from the Log Hours form | ✅ Done | Everyone |
| **My Hours** — personal time entries with period filters | ✅ Done | Everyone |
| **Team Hours** — all members' entries with filters | ✅ Done | Admin only |
| **Approvals** — approve/reject pending entries (fade-out animation) | ✅ Done | Approvers + Admin |
| **Job management** — toggle active/inactive, delete unused jobs | ✅ Done | Admin only |
| **Log on behalf of** — admin can submit hours for any member | ✅ Done | Admin only |
| **Wood Inventory** — available, spoken for, sold with status filters | ✅ Done | Everyone |
| **Finances** — income, expenses, net profit, member splits | ✅ Done | Admin only |
| **Dark/Light Mode** — toggle in nav, persists across sessions | ✅ Done | Everyone |
| **Offline Support** — cached pages, queued writes, auto-sync | ✅ Done | Everyone |
| **Production deployed** with auth flow end-to-end | ✅ Done | — |

## Roles

| Role | Can do | Needs approver? |
|------|--------|-----------------|
| **Admin** | Everything — see all entries, approve anyone, manage finances, manage jobs, log hours for anyone | No |
| **Member** | Log hours (auto-approved), see inventory, approve their kids, create new jobs | No |
| **Minor** | Log hours (pending approval), see inventory, create new jobs | Yes |

## Tech Stack

- **Backend:** Django 5 + [Django Ninja](https://django-ninja.dev/) (REST API) + [HTMX](https://htmx.org/)
- **Frontend:** [Svelte 5](https://svelte.dev/) "islands" mounted into Django templates via [Vite](https://vite.dev/)
- **Styling:** [Tailwind CSS v4](https://tailwindcss.com/) with OKLCH colors, 37signals-inspired design
- **Auth:** [noegos-auth](https://github.com/mtzirkel/noegos-auth) (separate SvelteKit service) — JWT cookie, TOTP login
- **JWT:** PyJWT with `cryptography` (NOT python-jose — it lacks EdDSA support)
- **Database:** SQLite (dev), PostgreSQL (production)
- **PWA:** Service worker with offline cache + write queue

## Data Model

```
CoopMember (role: admin|member|minor, approver → CoopMember)
    ↓
TimeEntry (job, date, time_start, time_end, hours, location, status, approved_by)

Job (name, description, rate_multiplier, is_active)
WoodInventory (wood_type, quantity, status, buyer, location)
Income (date, amount, source)        — admin only
Expense (date, amount, category)     — admin only
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

Dev mode auto-logs you in as an admin user (no auth service needed) —
controlled by `NOEGOS_AUTH_DEV_BYPASS` which defaults to `True` when `DEBUG=True`.

## Production Deployment

Live on the **badger** Linode (Ubuntu 24.04, ~$5/month). Sister apps share the same box.

```
noegosunderwater.com
├── auth.noegosunderwater.com  → noegos-auth (SvelteKit/Node)  ✅ live
├── coop.noegosunderwater.com  → The Coop (Django/Gunicorn)    ✅ live
├── chat.noegosunderwater.com  → Campfire (future)
└── board.noegosunderwater.com → Fizzy (future)
```

- Postgres standalone on the box (not in Docker) — `the_coop` database
- Nginx reverse proxy → gunicorn unix socket at `/run/the-coop/gunicorn.sock`
- systemd: `the-coop.service` + `the-coop.socket`
- Let's Encrypt SSL via certbot, auto-renewing
- DNS at Namecheap, cookie domain `.noegosunderwater.com` covers all subdomains
- App lives at `/srv/the-coop/`, env file at `/srv/the-coop/.env` (chmod 600)

### Deploying an update

```bash
ssh badger
cd /srv/the-coop
git pull
~/.local/bin/uv sync
cd frontend && npm run build && cd ..
~/.local/bin/uv run python manage.py migrate
~/.local/bin/uv run python manage.py collectstatic --noinput
sudo systemctl restart the-coop
```

## What's Next

1. **Income/expense forms** in the web UI (currently admin panel + API only)
2. **PWA icons** for install-to-homescreen
3. **Push notifications** for approval alerts (parents get notified when kids log hours)
4. **Campfire + Fizzy** bolt-ons for team chat and task planning
5. **Member self-service** — let members edit their own display name, see their YTD totals
