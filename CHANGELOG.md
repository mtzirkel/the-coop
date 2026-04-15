# Changelog

## 2026-04-14 — Production Launch

The Coop and noegos-auth went live on the badger Linode tonight. A bunch of fixes and features landed in the same session getting them deployable.

### The Coop

**New features**
- **Inline job creation from the Log Hours form.** Pick "+ Add new job…" at the bottom of the dropdown, type a name, and submitting the form creates the job and logs the hours in one shot. (`POST /api/jobs/` — open to all members; idempotent on name; reactivates soft-deleted jobs.)
- **Admin job management page (`/jobs/`).** Lists every job with its entry count. Toggle active/inactive via HTMX swap. Delete jobs with zero entries (refused for jobs with history so cascading deletes don't lose work).
- **Admins can log hours on behalf of any member.** A "Logging for" dropdown appears at the top of the Log Hours form for admins. Defaults to "Myself"; selecting another member submits with `member_id`. Auto-approved with `approved_by` recording the admin for the audit trail.
- **MIT license + README + SCOPE.md** added so the repo can go public on GitHub.

**Bug fixes**
- **JWT verification was crashing** on every real cookie. `python-jose==3.5.0` doesn't support EdDSA at all — its `ALGORITHMS.SUPPORTED` set excludes it entirely. Replaced with PyJWT (`pyjwt[crypto]`). Now uses `PyJWKClient` for JWKS fetching and caching, with a fallback that picks the first matching-algorithm key when a token has no `kid` header.
- **Production settings polish** — STATICFILES_DIRS only includes `frontend/dist/` if it exists (so dev `manage.py check` doesn't warn before the first Vite build). WhiteNoise's compressed manifest storage is gated behind `DEBUG=False`.

**Production deploy (badger Linode)**
- Cloned to `/srv/the-coop/`, Postgres database `the_coop` with generated password
- systemd: `the-coop.service` + `the-coop.socket` running gunicorn on a unix socket
- Nginx vhost at `/etc/nginx/sites-available/the-coop`, SSL via Let's Encrypt
- Tests: 45 Django tests + audit script all green
- Live at https://coop.noegosunderwater.com

### NoEgos Auth

**Bug fixes**
- **`return_to` parameter name mismatch.** Coop's middleware redirects with `?return_to=...` but the auth login was reading `?return`. After login, users were always dropped on the auth dashboard instead of bounced back to wherever they came from. Both `load` and the form action now read `return_to`.
- **Open redirect vulnerability.** Even if the parameter had matched, the action redirected to whatever URL was provided — `/login?return_to=https://evil.com` would have worked. Added `validateReturnTo()` helper that accepts:
  - Relative paths (in-app redirects)
  - URLs whose hostname matches a registered app's `apps.url`
  - URLs whose hostname is the cookie domain or a subdomain of it
  - Anything else returns `null` and falls back to `/`
- **JWTs now include a `kid` header** (`noegos-auth-signing`). Strict JWKS consumers like Python's `PyJWKClient.get_signing_key_from_jwt()` require it. Without the kid we were silently failing for every Python-side integration.

**Tests**
- 7 new vitest cases for `validateReturnTo` covering relative paths, protocol-relative tricks, malformed URLs, external origin rejection, registered-app matching, and exact-hostname enforcement (no substring smuggling)
- Total: 31 passing

**Production deploy (badger Linode)**
- Cloned to `/srv/noegos-auth/`, Postgres database `noegos_auth`
- systemd: `noegos-auth.service` running the SvelteKit Node adapter on `127.0.0.1:3001`
- Nginx vhost at `/etc/nginx/sites-available/noegos-auth`, SSL via Let's Encrypt
- Live at https://auth.noegosunderwater.com
- Travis bootstrapped as the first admin via `/seed`, registered "coop" as an app, granted himself admin role on it

### Infrastructure

- **Set up SSH access to badger** as a non-root `twomed` user with passwordless sudo via `/etc/sudoers.d/twomed`
- **Generated `~/.ssh/id_ed25519` on twomed-home** and added it to badger and GitHub
- **Installed Node 22 + uv on badger** (no Docker — apps run as native systemd services)
- **DNS records added at Namecheap** for `auth.noegosunderwater.com` and `coop.noegosunderwater.com` → `172.232.161.246`
