import logging
import time
import uuid
from dataclasses import dataclass, field

import httpx
import jwt
from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

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


# PyJWKClient handles its own caching — instantiate lazily
_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient | None:
    """Return the cached PyJWKClient, creating it on first use."""
    global _jwk_client
    if _jwk_client is None:
        try:
            _jwk_client = PyJWKClient(
                f"{settings.NOEGOS_AUTH_URL}/api/jwks",
                cache_keys=True,
                lifespan=3600,
            )
        except Exception:
            logger.exception("Failed to initialize JWK client")
            return None
    return _jwk_client


def _resolve_signing_key(client: PyJWKClient, token: str):
    """
    Find the signing key for a token. Prefers matching on the token's
    `kid` header, but if the token doesn't carry a kid we fall back to
    the first key in the JWKS with a matching algorithm. This is needed
    because noegos-auth currently signs without a kid.
    """
    # Try the standard path first — works when the token has a kid claim
    try:
        return client.get_signing_key_from_jwt(token).key
    except Exception:
        pass

    # Fall back: pick a key that matches the token's algorithm
    unverified_header = jwt.get_unverified_header(token)
    token_alg = unverified_header.get("alg")
    for key in client.get_jwk_set().keys:
        if getattr(key, "algorithm_name", None) == token_alg:
            return key.key
    return None


def verify_token(token: str) -> AuthUser | None:
    """Verify a noegos-auth JWT and return an AuthUser, or None if invalid."""
    client = _get_jwk_client()
    if client is None:
        return None

    try:
        signing_key = _resolve_signing_key(client, token)
        if signing_key is None:
            logger.debug("No JWKS key found for token")
            return None

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["EdDSA"],
            options={"verify_aud": False, "verify_iss": False},
        )
        return AuthUser(
            id=payload.get("sub", ""),
            username=payload.get("username", ""),
            is_admin=payload.get("admin", False),
            apps=payload.get("apps", []),
        )
    except PyJWTError:
        logger.debug("JWT verification failed", exc_info=True)
        return None
    except Exception:
        # Log unexpected errors but still return None — don't break requests
        logger.exception("Unexpected error verifying JWT")
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
