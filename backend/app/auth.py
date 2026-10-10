import hmac
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import schemas
from app.config import get_settings

# auto_error=False so a missing header reaches require_token and gets the same
# 401 as a wrong token.
bearer_scheme = HTTPBearer(auto_error=False)


def require_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> None:
    """Check the Bearer token, but only when API_TOKEN is set."""
    expected = get_settings().api_token
    if expected is None:
        return
    supplied = credentials.credentials if credentials else ""
    if not hmac.compare_digest(supplied.encode(), expected.get_secret_value().encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Router settings shared by every endpoint except /api/health.
PROTECTED: dict[str, Any] = {
    "dependencies": [Depends(require_token)],
    "responses": {401: {"model": schemas.ErrorDetail, "description": "Missing or invalid token"}},
}
