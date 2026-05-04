import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from unittest.mock import patch
from app.middleware.auth import verify_token

def make_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

def test_verify_token_returns_payload_on_valid_token():
    fake_payload = {"sub": "user-uuid-123", "role": "authenticated"}
    with patch("app.middleware.auth.jwt.decode", return_value=fake_payload):
        result = verify_token(make_credentials("valid.token.here"))
    assert result["sub"] == "user-uuid-123"

def test_verify_token_raises_401_on_invalid_token():
    from jwt.exceptions import InvalidTokenError
    with patch("app.middleware.auth.jwt.decode", side_effect=InvalidTokenError("bad")):
        with pytest.raises(HTTPException) as exc_info:
            verify_token(make_credentials("invalid.token"))
    assert exc_info.value.status_code == 401
