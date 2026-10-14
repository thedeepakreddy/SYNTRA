"""Production OIDC/JWT cryptographic token verification interface with JWKS key rotation."""

import logging
from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from syntra.api.auth.models import AuthenticatedUser
from syntra.core.config import Settings
from syntra.domain.entities import MembershipRole

logger = logging.getLogger(__name__)

# Cached JWKS client instance indexed by URL to avoid re-initializing HTTP clients
_jwks_clients: dict[str, PyJWKClient] = {}


def get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Retrieve or initialize a cached PyJWKClient for JWKS key rotation."""
    if jwks_url not in _jwks_clients:
        _jwks_clients[jwks_url] = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwks_clients[jwks_url]


def verify_and_decode_jwt(token: str, settings: Settings) -> dict[str, Any]:
    """Cryptographically verify JWT token against configured OIDC JWKS or symmetric secret.

    Validates:
    1. Cryptographic signature (with OIDC JWKS key rotation or symmetric HMAC secret)
    2. Expiration (exp)
    3. Audience (aud) if configured
    4. Issuer (iss) if configured
    """
    # 1. Unverified header check to inspect algorithm and key id
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Malformed JWT header: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    alg = header.get("alg")
    if not alg or alg.lower() == "none":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Insecure 'none' algorithm is rejected.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Determine signing key
    key: Any = None
    if settings.oidc_jwks_url:
        try:
            jwks_client = get_jwks_client(settings.oidc_jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key
        except Exception as exc:
            logger.warning("JWKS key retrieval failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unable to verify signature with IdP JWKS: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    elif settings.jwt_secret_key:
        key = settings.jwt_secret_key
    else:
        # Neither OIDC nor secret key configured
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Production Identity Provider is not configured. Set SYNTRA_OIDC_ISSUER, "
                "SYNTRA_OIDC_AUDIENCE, and SYNTRA_OIDC_JWKS_URL (or SYNTRA_JWT_SECRET_KEY for test environments)."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Decode and verify payload
    decode_kwargs: dict[str, Any] = {
        "algorithms": [alg],
        "options": {
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": bool(settings.oidc_audience),
            "verify_iss": bool(settings.oidc_issuer),
        },
    }
    if settings.oidc_audience:
        decode_kwargs["audience"] = settings.oidc_audience
    if settings.oidc_issuer:
        decode_kwargs["issuer"] = settings.oidc_issuer

    try:
        claims = jwt.decode(token, key=key, **decode_kwargs)
        return claims
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token audience mismatch: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidIssuerError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token issuer mismatch: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token cryptographic signature verification failed.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def parse_authenticated_user_from_claims(claims: dict[str, Any]) -> AuthenticatedUser:
    """Extract strongly-typed AuthenticatedUser from validated claims."""
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required 'sub' subject claim.",
        )
    try:
        user_id = UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Claim 'sub' must be a valid UUID.",
        ) from exc

    org_id_claim = claims.get("org_id") or claims.get("tenant_id")
    if not org_id_claim:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required 'org_id' multi-tenant claim.",
        )
    try:
        org_id = UUID(str(org_id_claim))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Claim 'org_id' must be a valid UUID.",
        ) from exc

    role_str = str(claims.get("role", "developer")).lower()
    try:
        role = MembershipRole(role_str)
    except ValueError:
        role = MembershipRole.VIEWER

    email = claims.get("email") or f"{user_id}@syntra.local"
    is_sa = bool(claims.get("is_service_account", False))

    return AuthenticatedUser(
        user_id=user_id,
        email=email,
        org_id=org_id,
        role=role,
        is_service_account=is_sa,
        claims=claims,
    )
