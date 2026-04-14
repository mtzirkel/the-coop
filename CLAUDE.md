# The Coop

Community co-op work tracker. Django backend + Svelte islands + HTMX.
~10 neighborhood members tracking hours, finances, and profit splits.

## Stack
- **Backend:** Django 5 + Ninja (API) + HTMX
- **Frontend:** Svelte 5 "islands" mounted into Django templates via Vite
- **Styling:** Tailwind CSS v4, 37signals-inspired minimal aesthetic
- **Auth:** noegos-auth (dev bypass auto-enabled when `DEBUG=True`)

## Dev Setup
```bash
./bin/dev          # starts Django :8000 + Vite :5173
```

## Running Tests
```bash
uv run python manage.py test coop -v2    # tests
uv run python manage.py check            # system checks
uv run python bin/audit-tests            # test gap auditor
```

## Architecture
- **HTMX** for simple interactions (click → swap a div, form submit → replace row)
- **Svelte islands** only where you need real client-side state or animation
- Never add SPA patterns — this is a server-rendered app with interactive islands
- New Svelte components go in `frontend/src/islands/` and mount via `data-svelte-component`
- Templates go in `templates/coop/` (full pages) or `templates/partials/` (HTMX fragments)

## Auth
- Access `request.auth_user` in views for the authenticated user
- `NOEGOS_AUTH_DEV_BYPASS=True` is on by default in DEBUG — auto-logs in as admin
- Tests use `@override_settings(NOEGOS_AUTH_DEV_BYPASS=True)` via `BaseCoopTest`
