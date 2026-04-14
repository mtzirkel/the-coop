import logging
import time
import uuid
from dataclasses import dataclass, field

import httpx
from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect
from jose import jwt
from jose.exceptions import JWTError

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    """User info extracted from a verified noegos-auth JWT."""

    id: str
    username: str
    is_admin: bool = False
    apps: list = field(default_factory=list)

    @property
    def coop_role(self):
        """Get the user's role for the coop app from their JWT claims."""
        for app in self.apps:
            if app.get("slug") == "coop":
                return app.get("role", "user")
        return None

    @property
    def has_coop_access(self):
        return self.coop_role is not None


# Cache JWKS keys in memory — refresh every hour
_jwks_cache = {"keys": None, "fetched_at": 0}
JWKS_CACHE_TTL = 3600  # 1 hour


def _get_jwks():
    """Fetch and cache the public keys from noegos-auth."""
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < JWKS_CACHE_TTL:
        return _jwks_cache["keys"]

    try:
        resp = httpx.get(
            f"{settings.NOEGOS_AUTH_URL}/api/jwks",
            timeout=5.0,
        )
        resp.raise_for_status()
        jwks = resp.json()
        _jwks_cache["keys"] = jwks
        _jwks_cache["fetched_at"] = now
        logger.info("Refreshed JWKS from noegos-auth")
        return jwks
    except Exception:
        logger.exception("Failed to fetch JWKS from noegos-auth")
        # Return stale cache if available
        if _jwks_cache["keys"]:
            return _jwks_cache["keys"]
        return None


def verify_token(token: str) -> AuthUser | None:
    """Verify a noegos-auth JWT and return an AuthUser, or None if invalid."""
    jwks = _get_jwks()
    if not jwks:
        return None

    try:
        # python-jose can verify directly from a JWKS dict
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["EdDSA"],
            options={"verify_aud": False},
        )
        return AuthUser(
            id=payload.get("sub", ""),
            username=payload.get("username", ""),
            is_admin=payload.get("admin", False),
            apps=payload.get("apps", []),
        )
    except JWTError:
        logger.debug("JWT verification failed", exc_info=True)
        return None


def _dev_user() -> AuthUser:
    """Create a fake dev user when NOEGOS_AUTH_DEV_BYPASS is set."""
    return AuthUser(
        id=str(getattr(settings, "NOEGOS_AUTH_DEV_USER_ID", uuid.UUID(int=1))),
        username=getattr(settings, "NOEGOS_AUTH_DEV_USERNAME", "dev"),
        is_admin=True,
        apps=[{"slug": "coop", "name": "The Coop", "role": "admin"}],
    )


class NoEgosAuthMiddleware:
    """
    Reads the noegos_auth cookie, verifies the JWT, and attaches
    the user info to request.auth_user.

    Public paths (health checks, static files) skip auth.
    All other paths redirect to the auth service login if not authenticated.

    Set NOEGOS_AUTH_DEV_BYPASS=True in settings to skip auth in development.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.dev_bypass = getattr(settings, "NOEGOS_AUTH_DEV_BYPASS", False)

    def __call__(self, request: HttpRequest):
        request.auth_user = None

        # Dev bypass — skip JWT verification entirely
        if self.dev_bypass:
            request.auth_user = _dev_user()
            return self.get_response(request)

        # Skip auth for public paths
        for path in settings.NOEGOS_AUTH_PUBLIC_PATHS:
            if request.path.startswith(path):
                return self.get_response(request)

        # Read the cookie
        token = request.COOKIES.get(settings.NOEGOS_AUTH_COOKIE)
        if token:
            request.auth_user = verify_token(token)

        # If no valid user, redirect to auth login
        if not request.auth_user:
            login_url = settings.NOEGOS_AUTH_LOGIN_REDIRECT
            current_url = request.build_absolute_uri()
            return HttpResponseRedirect(f"{login_url}?return_to={current_url}")

        return self.get_response(request)
