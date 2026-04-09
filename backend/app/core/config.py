from pydantic_settings import BaseSettings
from typing import List, Optional
import json
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "OppGrid API"
    API_V1_PREFIX: str = "/api/v1"

    # Database - Support both DATABASE_URL and REPLIT_DB_URL
    DATABASE_URL: str = ""

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # URLs - Support Replit environment
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # CORS - allow all origins by default for development (set explicit origins in production).
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Basic rate limiting (single-process best-effort).
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 300

    # Background jobs (single-runtime in-process scheduler)
    JOBS_ENABLED: bool = True
    ESCROW_RELEASE_JOB_ENABLED: bool = True
    ESCROW_RELEASE_JOB_INTERVAL_SECONDS: int = 900  # 15 minutes
    APIFY_IMPORT_JOB_ENABLED: bool = False  # enable when APIFY_API_TOKEN is configured
    APIFY_IMPORT_JOB_INTERVAL_SECONDS: int = 86400  # daily
    APIFY_ACTOR_ID: str = "trudax/reddit-scraper-lite"
    AI_ANALYSIS_JOB_ENABLED: bool = True
    AI_ANALYSIS_BATCH_SIZE: int = 20

    # Stripe subscription reconciliation (defense-in-depth for missed webhooks).
    # Set STRIPE_RECONCILE_JOB_ENABLED=false to disable (e.g. during local dev without Stripe keys).
    # STRIPE_RECONCILE_JOB_INTERVAL_SECONDS controls how often subscriptions are re-synced from Stripe.
    STRIPE_RECONCILE_JOB_ENABLED: bool = True
    STRIPE_RECONCILE_JOB_INTERVAL_SECONDS: int = 3600  # 1 hour

    # Email Configuration (Resend)
    RESEND_API_KEY: Optional[str] = None
    FROM_EMAIL: Optional[str] = "noreply@yourdomain.com"

    # OAuth Configuration (Google)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # OAuth Configuration (GitHub)
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # If DATABASE_URL is not set, try REPLIT_DB_URL
        if not self.DATABASE_URL:
            replit_db_url = os.getenv("REPLIT_DB_URL")
            if replit_db_url:
                self.DATABASE_URL = replit_db_url
            else:
                # Fallback for local development
                self.DATABASE_URL = os.getenv(
                    "DATABASE_URL",
                    "postgresql://user:password@localhost:5432/oppgrid_db"
                )

        # Set frontend and backend URLs for Replit environment
        repl_slug = os.getenv("REPL_SLUG")
        repl_owner = os.getenv("REPL_OWNER")
        if repl_slug and repl_owner:
            base_url = f"https://{repl_slug}.{repl_owner}.repl.co"
            if self.BACKEND_URL == "http://localhost:8000":
                self.BACKEND_URL = base_url
            if self.FRONTEND_URL == "http://localhost:3000":
                self.FRONTEND_URL = base_url

        # Normalize URLs (support env values like "foo.repl.co" without scheme)
        self.BACKEND_URL = self._normalize_base_url(self.BACKEND_URL, default_scheme="http")
        self.FRONTEND_URL = self._normalize_base_url(self.FRONTEND_URL, default_scheme="http")

    @staticmethod
    def _normalize_base_url(url: str, default_scheme: str = "http") -> str:
        if not url:
            return url

        url = url.strip()

        # Strip trailing slash for consistent joining
        if url.endswith("/"):
            url = url.rstrip("/")

        if url.startswith("http://") or url.startswith("https://"):
            return url

        # Heuristic: Replit domains should be https by default.
        scheme = "https" if (".repl.co" in url or ".replit.dev" in url) else default_scheme
        return f"{scheme}://{url}"

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins if they're stored as JSON string"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            try:
                return json.loads(self.BACKEND_CORS_ORIGINS)
            except json.JSONDecodeError:
                return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS

    def is_cors_wildcard(self) -> bool:
        origins = self.get_cors_origins()
        return len(origins) == 1 and origins[0] == "*"


settings = Settings()
