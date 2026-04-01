import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.trace_id import TraceIdMiddleware, install_trace_id_factory, configure_app_logging
from app.routers import (
    admin,
    admin_models,
    agreements,
    billing,
    ai_analysis,
    ai_chat,
    ai_cofounder,
    ai_engine,
    analytics,
    auth,
    collections,
    command_center,
    comments,
    consultant,
    contact,
    copilot,
    expert_collaboration,
    experts,
    follows,
    generated_reports,
    google_scraping,
    reports,
    idea_engine,
    idea_validations,
    leads,
    leads_marketplace,
    lifecycle,
    linkedin,
    magic_link,
    map_data,
    maps,
    milestones,
    moderation,
    notifications,
    oauth,
    opportunities,
    payments,
    profiles,
    quick_actions,
    replit_auth,
    report_pricing,
    sba,
    scraper,
    social,
    stripe_webhook,
    subscriptions,
    teams,
    two_factor,
    upwork,
    users,
    validations,
    watchlist,
    webhook,
    webhooks,
    websocket_router,
    workspaces,
    byok,
    affiliate_tools,
    public_api,
    ai_preferences,
    workspace_map,
    workspace_digital,
    deep_clone,
    saved_layers,
    foot_traffic,
    saved_searches,
    enhanced_workspaces,
    agent,
    market,
    opportunity_collections,
    opportunity_lifecycle,
)

install_trace_id_factory()
configure_app_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
_cors_origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Credentials cannot be used with wildcard origins; automatically disable in that case.
    allow_credentials=False if settings.is_cors_wildcard() else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic platform hardening (best-effort, single-runtime).
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    enabled=settings.RATE_LIMIT_ENABLED,
    default_limit_per_minute=settings.RATE_LIMIT_DEFAULT_PER_MINUTE,
)
app.add_middleware(TraceIdMiddleware)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(opportunity_collections.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Opportunity Collections"])
app.include_router(opportunity_lifecycle.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Opportunity Lifecycle"])
app.include_router(opportunities.router, prefix=f"{settings.API_V1_PREFIX}/opportunities", tags=["Opportunities"])
app.include_router(saved_searches.router, prefix=f"{settings.API_V1_PREFIX}/saved-searches", tags=["Saved Searches"])
app.include_router(validations.router, prefix=f"{settings.API_V1_PREFIX}/validations", tags=["Validations"])
app.include_router(comments.router, prefix=f"{settings.API_V1_PREFIX}/comments", tags=["Comments"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])
app.include_router(watchlist.router, prefix=f"{settings.API_V1_PREFIX}/watchlist", tags=["Watchlist"])
app.include_router(collections.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Workhub"])
app.include_router(two_factor.router, prefix=f"{settings.API_V1_PREFIX}/2fa", tags=["Two-Factor Auth"])
app.include_router(oauth.router, prefix=f"{settings.API_V1_PREFIX}/oauth", tags=["OAuth"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Admin"])
app.include_router(admin_models.router, tags=["Admin - AI Models"])
app.include_router(billing.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Billing"])
app.include_router(moderation.router, prefix=f"{settings.API_V1_PREFIX}/moderation", tags=["Moderation"])
app.include_router(subscriptions.router, prefix=f"{settings.API_V1_PREFIX}/subscriptions", tags=["Subscriptions"])
app.include_router(social.router, prefix=f"{settings.API_V1_PREFIX}/social", tags=["Social Sharing"])
app.include_router(follows.router, prefix=f"{settings.API_V1_PREFIX}/follows", tags=["Follows"])
app.include_router(profiles.router, prefix=f"{settings.API_V1_PREFIX}/profiles", tags=["Profiles"])
app.include_router(experts.router, prefix=f"{settings.API_V1_PREFIX}/experts", tags=["Experts"])
app.include_router(ai_engine.router, prefix=f"{settings.API_V1_PREFIX}/ai-engine", tags=["AI Engine"])
app.include_router(payments.router, prefix=f"{settings.API_V1_PREFIX}/payments", tags=["Payments"])
app.include_router(stripe_webhook.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Stripe Webhooks"])
app.include_router(agreements.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Agreements"])
app.include_router(milestones.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Milestones"])
app.include_router(websocket_router.router, prefix=f"{settings.API_V1_PREFIX}", tags=["WebSocket"])
app.include_router(ai_chat.router, prefix=f"{settings.API_V1_PREFIX}/ai", tags=["AI Chat"])
app.include_router(ai_analysis.router, prefix=f"{settings.API_V1_PREFIX}/ai-analysis", tags=["AI Analysis"])
app.include_router(idea_engine.router, prefix=f"{settings.API_V1_PREFIX}/idea-engine", tags=["Idea Engine"])
app.include_router(idea_validations.router, prefix=f"{settings.API_V1_PREFIX}/idea-validations", tags=["Idea Validations"])
app.include_router(webhook.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Webhooks"])
app.include_router(scraper.router, prefix=f"{settings.API_V1_PREFIX}/scraper", tags=["Scraper"])
# Mount at /auth for Replit Auth user-facing flow (login, callback)
app.include_router(replit_auth.router, prefix="/auth", tags=["Replit Auth"])
# Mount callback at root level for /__repl_auth_callback endpoint
app.include_router(replit_auth.router, prefix="", tags=["Replit Auth Callback"])
app.include_router(magic_link.router, prefix=f"{settings.API_V1_PREFIX}/magic-link", tags=["Magic Link Auth"])
app.include_router(contact.router, prefix=f"{settings.API_V1_PREFIX}/contact", tags=["Contact"])
app.include_router(leads.router, prefix=f"{settings.API_V1_PREFIX}/admin/leads", tags=["Admin Leads"])
app.include_router(leads_marketplace.router, prefix=f"{settings.API_V1_PREFIX}/marketplace/leads", tags=["Leads Marketplace"])
app.include_router(lifecycle.router, prefix=settings.API_V1_PREFIX, tags=["Lifecycle"])
app.include_router(generated_reports.router, prefix=f"{settings.API_V1_PREFIX}/reports", tags=["Generated Reports"])
app.include_router(consultant.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Consultant Studio"])
app.include_router(quick_actions.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Quick Actions"])
app.include_router(webhooks.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Data Webhooks"])
app.include_router(webhooks.apify_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Apify Webhook"])
app.include_router(map_data.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Map Data"])
app.include_router(maps.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Maps"])
app.include_router(linkedin.router, prefix=f"{settings.API_V1_PREFIX}/auth/linkedin", tags=["LinkedIn OAuth"])
app.include_router(command_center.router, prefix=f"{settings.API_V1_PREFIX}/command-center", tags=["Command Center"])
app.include_router(google_scraping.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Google Scraping"])
app.include_router(workspaces.router, prefix=f"{settings.API_V1_PREFIX}/workspaces", tags=["Workspaces"])
app.include_router(ai_cofounder.router, prefix=f"{settings.API_V1_PREFIX}", tags=["AI Co-Founder"])
app.include_router(copilot.router, prefix=f"{settings.API_V1_PREFIX}", tags=["AI Copilot"])
app.include_router(report_pricing.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Report Pricing"])
app.include_router(expert_collaboration.router, prefix=f"{settings.API_V1_PREFIX}/expert-network", tags=["Expert Collaboration"])
app.include_router(upwork.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Upwork Integration"])
app.include_router(sba.router, prefix=f"{settings.API_V1_PREFIX}/sba", tags=["SBA Funding"])
app.include_router(byok.router, tags=["BYOK"])
app.include_router(affiliate_tools.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Affiliate Tools"])
app.include_router(reports.router, tags=["Report Templates"])
app.include_router(teams.router, prefix=f"{settings.API_V1_PREFIX}/teams", tags=["Teams"])
app.include_router(public_api.router, prefix=f"{settings.API_V1_PREFIX}/public", tags=["Public API"])
app.include_router(ai_preferences.router, prefix=f"{settings.API_V1_PREFIX}", tags=["AI Preferences"])
app.include_router(workspace_map.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Workspace Map"])
app.include_router(workspace_digital.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Workspace Digital"])
app.include_router(deep_clone.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Deep Clone"])
app.include_router(saved_layers.router, prefix=f"{settings.API_V1_PREFIX}/saved-layers", tags=["Saved Layers"])
app.include_router(foot_traffic.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Foot Traffic"])
app.include_router(enhanced_workspaces.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Enhanced Workspaces"])
app.include_router(agent.router, tags=["Agent API"])
app.include_router(market.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Market Intelligence"])


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        from app.db.database import initialize_database
        from sqlalchemy import text
        from app.services.job_runner import start_background_jobs

        logger.info("Initializing database connection...")
        engine = initialize_database()

        # Best practice: rely on Alembic migrations, not runtime create_all().
        # We do a lightweight check and log a clear warning if migrations haven't run.
        #
        # If REQUIRE_MIGRATIONS=1, we fail startup when migrations aren't applied.
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM alembic_version LIMIT 1"))
        except Exception as e:
            require_migrations = os.getenv("REQUIRE_MIGRATIONS") == "1"
            msg = (
                "Database migrations may not have been applied yet. "
                "Run `alembic upgrade head` in /workspace/backend. "
                f"Details: {e}"
            )
            if require_migrations:
                raise RuntimeError(msg) from e
            logger.warning(msg)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Application starting without database connection. Check DATABASE_URL in Secrets.")

    # Start background jobs (best-effort; will no-op if disabled)
    try:
        start_background_jobs()
    except Exception as e:
        logger.warning("Failed to start background jobs: %s", e)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    from app.db.database import SessionLocal
    from sqlalchemy import text

    db_ok = False
    db_error: str | None = None
    migration_status: dict = {"status": "unknown"}

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_ok = True

        # Migration visibility: report current revision and whether alembic_version exists.
        current_rev: str | None = None
        try:
            row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
            current_rev = row[0] if row else None
        except Exception as e:
            migration_status = {
                "status": "missing",
                "detail": f"alembic_version table not found or unreadable: {e}",
            }
        else:
            # Optional: compare to script head when Alembic is available.
            head_rev: str | None = None
            try:
                from alembic.config import Config
                from alembic.script import ScriptDirectory

                cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
                script = ScriptDirectory.from_config(cfg)
                heads = script.get_heads()
                head_rev = heads[0] if heads else None
            except Exception:
                head_rev = None

            if current_rev and head_rev and current_rev != head_rev:
                migration_status = {
                    "status": "behind",
                    "current_revision": current_rev,
                    "head_revision": head_rev,
                }
            else:
                migration_status = {
                    "status": "applied",
                    "current_revision": current_rev,
                    "head_revision": head_rev,
                }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_error = str(e)
    finally:
        try:
            db.close()
        except Exception:
            pass

    overall = "healthy" if db_ok and migration_status.get("status") in {"applied", "unknown"} else "degraded"
    return {
        "status": overall,
        "database": {"status": "connected" if db_ok else "error", "error": db_error},
        "migrations": migration_status,
    }


FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    if (FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
else:
    @app.get("/")
    def root():
        return {
            "message": "Welcome to OppGrid API",
            "docs": "/docs",
            "version": "1.0.0"
        }
