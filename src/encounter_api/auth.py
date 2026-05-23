"""Mock JWT authentication.

A bearer token signed with a shared HS256 secret stands in for real auth. It is
enough to exercise the security boundary, every request carries a verified
caller identity, without building an identity provider. The production path
(asymmetric ES384 keys from an IdP, verified against a rotating JWKS endpoint)
is described in the README.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from encounter_api.config import Settings, get_settings

_bearer_scheme = HTTPBearer(auto_error=True)


class Principal(BaseModel):
    """The authenticated caller derived from a verified token."""

    subject: str


def issue_token(
    subject: str,
    *,
    settings: Settings | None = None,
    expires_in: timedelta = timedelta(hours=1),
) -> str:
    """Mint a signed token for the given subject.

    This supports the docs examples and the test suite. It is not a login flow;
    in production tokens come from the identity provider, not from this service.
    """

    settings = settings or get_settings()
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def authenticate(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(subject=claims["sub"])


CurrentPrincipal = Annotated[Principal, Depends(authenticate)]
