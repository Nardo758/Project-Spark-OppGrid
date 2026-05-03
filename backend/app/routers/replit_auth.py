"""
Replit Auth Router - OIDC integration using Replit as identity provider
Uses database-backed session storage following Replit's recommended patterns
"""
import os
import secrets
import httpx
import hashlib
import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import jwt
from jwt import PyJWKClient

from app.db.database import get_db
from app.models.user import User
from app.models.oauth import OAuthToken
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter()

REPL_ID = os.environ.get('REPL_ID', '')
ISSUER_URL = os.environ.get('ISSUER_URL', 'https://replit.com/oidc').rstrip('/')
AUTHORIZATION_ENDPOINT = f"{ISSUER_URL}/auth"
TOKEN_ENDPOINT = f"{ISSUER_URL}/token"
END_SESSION_ENDPOINT = f"{ISSUER_URL}/session/end"
JWKS_URL = f"{ISSUER_URL}/jwks"
# When ISSUER_URL is overridden (e.g. local test mock OIDC server), skip TLS verify.
_OIDC_VERIFY_TLS = ISSUER_URL == 'https://replit.com/oidc'
SESSION_SECRET = os.environ.get('SESSION_SECRET')

if not SESSION_SECRET:
    import logging
    logging.warning("SESSION_SECRET not set - auth state tokens will use fallback key. Set SESSION_SECRET in production!")
    SESSION_SECRET = "dev-fallback-key-not-for-production"

SESSION_COOKIE_NAME = "oppgrid_session"
STATE_COOKIE_NAME = "auth_state"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30

_jwks_client = None


def is_secure_context(request: Request) -> bool:
    """Determine if the request is over HTTPS (for cookie security)"""
    forwarded_proto = request.headers.get('x-forwarded-proto', '')
    if forwarded_proto == 'https':
        return True
    return request.url.scheme == 'https'


def get_jwks_client():
    """Get cached JWKS client for token verification"""
    global _jwks_client
    if _jwks_client is None:
        if not _OIDC_VERIFY_TLS:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                _jwks_client = PyJWKClient(JWKS_URL, cache_keys=True, ssl_context=ctx)
            except TypeError:
                _jwks_client = PyJWKClient(JWKS_URL, cache_keys=True)
        else:
            _jwks_client = PyJWKClient(JWKS_URL, cache_keys=True)
    return _jwks_client


def generate_browser_session_key() -> str:
    """Generate a unique browser session key"""
    return uuid.uuid4().hex


def get_callback_url() -> str:
    """Get the callback URL for OAuth"""
    callback_path = "/__repl_auth_callback"
    
    # Priority 1: Use FRONTEND_URL if set (supports custom domains like oppgrid.com)
    frontend_url = os.environ.get('FRONTEND_URL', '')
    if frontend_url:
        base = frontend_url.strip().rstrip("/")
        if not (base.startswith("http://") or base.startswith("https://")):
            base = f"https://{base}"
        return f"{base}{callback_path}"
    
    # Priority 2: Fall back to REPLIT_DOMAINS for development
    replit_domains = os.environ.get('REPLIT_DOMAINS', '')
    if replit_domains:
        primary_domain = replit_domains.split(',')[0].strip()
        return f"https://{primary_domain}{callback_path}"
    
    return f"http://localhost:5000{callback_path}"


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge"""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    return code_verifier, code_challenge


def create_state_token(data: dict) -> str:
    """Create a signed state token for OAuth flow"""
    data['exp'] = datetime.now(timezone.utc) + timedelta(minutes=10)
    return jwt.encode(data, SESSION_SECRET, algorithm='HS256')


def verify_state_token(token: str) -> Optional[dict]:
    """Verify and decode a state token"""
    try:
        return jwt.decode(token, SESSION_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_id_token(id_token: str, nonce: Optional[str] = None) -> Dict[str, Any]:
    """Verify and decode the ID token from Replit"""
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "PS256"],
            issuer=ISSUER_URL if _OIDC_VERIFY_TLS else None,
            audience=REPL_ID,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": _OIDC_VERIFY_TLS,
                "verify_aud": True,
            }
        )
        
        if nonce and claims.get('nonce') != nonce:
            raise ValueError("Nonce mismatch - possible replay attack")
        
        return claims
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidIssuerError:
        raise ValueError("Invalid token issuer")
    except jwt.InvalidAudienceError:
        raise ValueError("Invalid token audience")
    except jwt.InvalidSignatureError:
        raise ValueError("Invalid token signature")
    except Exception as e:
        raise ValueError(f"Token validation failed: {str(e)}")


def get_or_create_session_key(request: Request, response: Response) -> str:
    """Get existing session key from cookie or create a new one"""
    session_key = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_key:
        session_key = generate_browser_session_key()
    return session_key


def store_oauth_token(
    db: Session,
    user_id: int,
    session_key: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_at: Optional[datetime]
):
    """Store OAuth token in database"""
    existing = db.query(OAuthToken).filter(
        OAuthToken.user_id == user_id,
        OAuthToken.browser_session_key == session_key,
        OAuthToken.provider == "replit"
    ).first()
    
    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.expires_at = expires_at
    else:
        oauth_token = OAuthToken(
            user_id=user_id,
            browser_session_key=session_key,
            provider="replit",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        db.add(oauth_token)
    
    db.commit()


def delete_oauth_token(db: Session, user_id: int, session_key: str):
    """Delete OAuth token from database"""
    db.query(OAuthToken).filter(
        OAuthToken.user_id == user_id,
        OAuthToken.browser_session_key == session_key,
        OAuthToken.provider == "replit"
    ).delete()
    db.commit()


@router.get("/login")
async def replit_login(
    request: Request,
    redirect_url: Optional[str] = None
):
    """Initiate Replit OIDC login flow with PKCE"""
    if not REPL_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Replit Auth not configured - REPL_ID not set"
        )
    
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    session_key = request.cookies.get(SESSION_COOKIE_NAME) or generate_browser_session_key()
    callback_url = get_callback_url()
    
    state_data = {
        'state': state,
        'nonce': nonce,
        'code_verifier': code_verifier,
        'redirect_url': redirect_url or '/discover.html',
        'callback_url': callback_url,
        'session_key': session_key
    }
    state_token = create_state_token(state_data)
    
    params = {
        'client_id': REPL_ID,
        'response_type': 'code',
        'redirect_uri': callback_url,
        'scope': 'openid profile email offline_access',
        'state': state,
        'nonce': nonce,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'prompt': 'login consent'
    }
    
    auth_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
    
    use_secure = is_secure_context(request)
    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state_token,
        max_age=600,
        httponly=True,
        secure=use_secure,
        samesite="lax"
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_key,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=use_secure,
        samesite="lax"
    )
    
    print(f"[Replit Auth] Login initiated, redirecting to: {auth_url}")
    return response


@router.get("/callback")
@router.get("/__repl_auth_callback")
async def replit_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle OIDC callback from Replit"""
    print(f"[Replit Auth] Callback received - code: {'present' if code else 'missing'}, state: {'present' if state else 'missing'}")
    
    if error:
        return RedirectResponse(url=f"/signin.html?error={error}&desc={error_description or ''}")
    
    if not code or not state:
        return RedirectResponse(url="/signin.html?error=missing_params")
    
    state_token = request.cookies.get(STATE_COOKIE_NAME)
    if not state_token:
        print("[Replit Auth] No state cookie found")
        return RedirectResponse(url="/signin.html?error=invalid_state")
    
    state_data = verify_state_token(state_token)
    if not state_data or state_data.get('state') != state:
        print("[Replit Auth] State mismatch or expired")
        return RedirectResponse(url="/signin.html?error=invalid_state")
    
    code_verifier = state_data['code_verifier']
    nonce = state_data['nonce']
    redirect_url = state_data['redirect_url']
    callback_url = state_data['callback_url']
    session_key = state_data['session_key']
    
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': callback_url,
        'client_id': REPL_ID,
        'code_verifier': code_verifier
    }
    
    try:
        async with httpx.AsyncClient(verify=_OIDC_VERIFY_TLS) as client:
            token_response = await client.post(
                TOKEN_ENDPOINT,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if token_response.status_code != 200:
                print(f"[Replit Auth] Token exchange failed: {token_response.text}")
                return RedirectResponse(url="/signin.html?error=token_exchange_failed")
            
            tokens = token_response.json()
    except Exception as e:
        print(f"[Replit Auth] Token exchange error: {e}")
        return RedirectResponse(url="/signin.html?error=token_exchange_error")
    
    id_token = tokens.get('id_token')
    if not id_token:
        return RedirectResponse(url="/signin.html?error=no_id_token")
    
    try:
        user_claims = verify_id_token(id_token, nonce)
        print(f"[Replit Auth] Token verified, claims: {json.dumps(user_claims, default=str)}")
    except ValueError as e:
        print(f"[Replit Auth] Token verification failed: {e}")
        return RedirectResponse(url="/signin.html?error=token_verification_failed")
    
    replit_user_id = str(user_claims.get('sub'))
    email = user_claims.get('email')
    first_name = user_claims.get('first_name', '')
    last_name = user_claims.get('last_name', '')
    profile_image = user_claims.get('profile_image_url')
    
    if not replit_user_id:
        return RedirectResponse(url="/signin.html?error=no_user_id")
    
    user = db.query(User).filter(
        User.oauth_provider == 'replit',
        User.oauth_id == replit_user_id
    ).first()
    
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.oauth_provider = 'replit'
            user.oauth_id = replit_user_id
            if profile_image:
                user.avatar_url = profile_image
    
    if not user:
        full_name = f"{first_name} {last_name}".strip() or f"User_{replit_user_id}"
        user_email = email if email else f"{replit_user_id}@replit.user"
        
        user = User(
            email=user_email,
            name=full_name,
            oauth_provider='replit',
            oauth_id=replit_user_id,
            avatar_url=profile_image,
            is_active=True,
            is_verified=True
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    
    print(f"[Replit Auth] User authenticated: {user.email}")
    
    replit_access_token = tokens.get('access_token')
    replit_refresh_token = tokens.get('refresh_token')
    expires_in = tokens.get('expires_in', 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    store_oauth_token(
        db=db,
        user_id=user.id,
        session_key=session_key,
        access_token=replit_access_token,
        refresh_token=replit_refresh_token,
        expires_at=expires_at
    )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    user_data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.name,
        "avatar_url": user.avatar_url,
        "is_verified": user.is_verified,
        "is_admin": user.is_admin
    }
    
    user_json = base64.urlsafe_b64encode(json.dumps(user_data).encode()).decode()
    
    use_secure = is_secure_context(request)
    
    # Redirect directly to destination - use short-lived cookies for token handoff
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.delete_cookie(STATE_COOKIE_NAME)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_key,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=use_secure,
        samesite="lax"
    )
    # Short-lived cookies to pass auth data to JavaScript (picked up on page load)
    response.set_cookie(
        key="auth_token",
        value=access_token,
        max_age=60,
        httponly=False,
        secure=use_secure,
        samesite="lax"
    )
    response.set_cookie(
        key="auth_user",
        value=user_json,
        max_age=60,
        httponly=False,
        secure=use_secure,
        samesite="lax"
    )
    
    return response


@router.get("/logout")
async def replit_logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """Logout and end Replit session"""
    session_key = request.cookies.get(SESSION_COOKIE_NAME)
    
    params = {
        'client_id': REPL_ID,
        'post_logout_redirect_uri': get_callback_url().rsplit('/', 1)[0]
    }
    
    logout_url = f"{END_SESSION_ENDPOINT}?{urlencode(params)}"
    
    response = RedirectResponse(url=logout_url)
    response.delete_cookie(SESSION_COOKIE_NAME)
    
    return response


@router.get("/status")
async def auth_status(request: Request):
    """Check if Replit Auth is configured"""
    return {
        "configured": bool(REPL_ID),
        "provider": "replit",
        "client_id": REPL_ID,
        "callback_url": get_callback_url(),
        "authorization_endpoint": AUTHORIZATION_ENDPOINT,
        "session_active": bool(request.cookies.get(SESSION_COOKIE_NAME))
    }


@router.get("/debug")
async def auth_debug():
    """Debug endpoint to show current configuration"""
    return {
        "repl_id": REPL_ID,
        "replit_dev_domain": os.environ.get('REPLIT_DEV_DOMAIN', 'not set'),
        "replit_domains": os.environ.get('REPLIT_DOMAINS', 'not set'),
        "callback_url": get_callback_url(),
        "issuer": ISSUER_URL,
        "authorization_endpoint": AUTHORIZATION_ENDPOINT,
        "token_endpoint": TOKEN_ENDPOINT,
        "jwks_url": JWKS_URL,
        "session_secret_configured": bool(SESSION_SECRET)
    }
