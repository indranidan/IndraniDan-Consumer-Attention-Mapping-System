"""
Authentication Routes
======================
Handles user registration, login, logout, and Google OAuth flow.

Endpoints:
    POST   /api/auth/register          Register a new user
    POST   /api/auth/login             Login with email/password
    POST   /api/auth/logout            Logout (frontend clears token)
    GET    /api/auth/roles             List available roles
    GET    /api/auth/google/login      Redirect to Google OAuth
    GET    /api/auth/google/callback   Handle Google OAuth callback
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from app.database.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    MessageResponse,
)
from app.schemas.user import RoleResponse
from app.services.auth_service import (
    register_user,
    authenticate_user,
    get_or_create_google_user,
    get_all_roles,
)
from app.core.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()

# ── Google OAuth Setup ────────────────────────────────────────
oauth = OAuth()

# Only register Google if credentials are configured
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ── Registration ──────────────────────────────────────────────
@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        409: {"description": "Email already exists"},
        404: {"description": "Role not found"},
        422: {"description": "Validation error"},
    },
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new user account.

    - Validates email uniqueness (409 if duplicate)
    - Validates role exists (404 if not)
    - Hashes password with bcrypt
    - Returns success message
    """
    register_user(db, payload)
    return MessageResponse(message="User registered successfully.")


# ── Login ─────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Account disabled"},
    },
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate with email and password.

    Returns a JWT access token with user info.
    """
    return authenticate_user(db, payload.email, payload.password)


# ── Logout ────────────────────────────────────────────────────
@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (server acknowledgement)",
)
def logout():
    """
    Logout endpoint.

    JWT is stateless — the frontend removes the token from storage.
    This endpoint exists for API completeness and logging purposes.
    """
    return MessageResponse(message="Logged out successfully.")


# ── List Roles ────────────────────────────────────────────────
@router.get(
    "/roles",
    response_model=list[RoleResponse],
    summary="List all available roles",
)
def list_roles(db: Session = Depends(get_db)):
    """
    Returns all predefined roles.
    Used by the registration form to populate the role dropdown.
    """
    return get_all_roles(db)


# ── Google OAuth: Initiate Login ──────────────────────────────
@router.get(
    "/google/login",
    summary="Redirect to Google OAuth",
    responses={
        503: {"description": "Google OAuth not configured"},
    },
)
async def google_login(request: Request):
    """
    Initiates the Google OAuth flow by redirecting the user
    to Google's consent screen.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


# ── Google OAuth: Callback ────────────────────────────────────
@router.get(
    "/google/callback",
    summary="Handle Google OAuth callback",
    name="google_callback",
)
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receives the OAuth callback from Google, extracts user info,
    creates or fetches the user, generates a JWT, and redirects
    to the frontend with the token.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured.",
        )

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with Google.",
        )

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not retrieve user information from Google.",
        )

    email = user_info.get("email")
    full_name = user_info.get("name", email.split("@")[0])

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account does not have an email address.",
        )

    result = get_or_create_google_user(db, email, full_name)

    # Redirect to frontend with token as query parameter
    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/google/callback"
        f"?access_token={result['access_token']}"
        f"&token_type={result['token_type']}"
        f"&user_name={result['user'].full_name}"
        f"&user_email={result['user'].email}"
        f"&user_role={result['user'].role}"
    )
    return RedirectResponse(url=redirect_url)
