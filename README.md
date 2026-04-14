# The Coop

A community co-op work tracker for a small neighborhood near East Glacier Park, Montana.
Track work hours, manage wood inventory, and split profits at year-end.

## Stack

- **Backend:** Django 5 + [Django Ninja](https://django-ninja.dev/) (REST API) + [HTMX](https://htmx.org/)
- **Frontend:** [Svelte 5](https://svelte.dev/) "islands" mounted into Django templates via [Vite](https://vite.dev/)
- **Styling:** [Tailwind CSS v4](https://tailwindcss.com/) with an OKLCH-based design system
- **Auth:** External JWT from [noegos-auth](https://github.com/mtzirkel/noegos-auth), verified via Django middleware
- **PWA:** Service worker with offline cache and write queue — works in the woods
- **Tests:** 35 Django tests, plus a test-coverage auditor (`bin/audit-tests`)

See [`SCOPE.md`](SCOPE.md) for the full project scope, feature list, and data model.

## Running Locally

```bash
# First time
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

## Design Philosophy

Inspired by [37signals' Fizzy and Campfire](https://dev.37signals.com/) — pill-shaped buttons,
subtle shadows over borders, OKLCH color space, vanilla CSS patterns. The color palette
draws from a Montana fall: aspen gold, larch amber, lodgepole pine green.

HTMX handles the "click this, swap that" interactions. Svelte islands only appear where
real client-side reactivity earns its weight (live-calculated time forms, stats widgets).
Never a full SPA.

## License

MIT — see [`LICENSE`](LICENSE).
