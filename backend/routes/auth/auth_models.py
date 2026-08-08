from pydantic import BaseModel, field_validator


def _not_blank(v):
    if isinstance(v, str) and not v.strip():
        raise ValueError("must not be empty or just whitespace")
    return v


class Login(BaseModel):
    """One login form for every password-based account: the admin and teams."""

    name: str
    password: str

    _check_not_empty = field_validator("*")(_not_blank)


class AdminSetup(BaseModel):
    """First-run setup: the name and password the admin will log in with."""

    name: str
    password: str

    _check_not_empty = field_validator("*")(_not_blank)

    @field_validator("password")
    def check_length(cls, v):
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class AgentLogin(BaseModel):
    """Agent login request model"""

    api_key: str

    _check_not_empty = field_validator("api_key")(_not_blank)


class TokenResponse(BaseModel):
    """Access token issued on a successful login, with the role it carries so
    the frontend can route without decoding the JWT first."""

    access_token: str
    token_type: str = "bearer"
    role: str
