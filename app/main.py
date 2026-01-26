import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.db.database import Base, engine
from app.auth import routes as auth_routes

app = FastAPI(
    title="VPM Backend API",
    description="SAP Data Dashboard - Auth, Intake Forms, OTP verification, password reset, etc.",
    version="1.0.0",
)

# Rate limiting setup (optional - install slowapi for rate limiting)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
    # Initialize rate limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    RATE_LIMITING_ENABLED = True
except ImportError:
    print("WARNING: slowapi not installed. Rate limiting disabled. Install with: pip install slowapi httpx pillow")
    RATE_LIMITING_ENABLED = False
    # Create a dummy limiter object
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    app.state.limiter = DummyLimiter()

# CORS to allow external frontend(s)
# Support multiple frontend URLs from environment
frontend_urls = []
if os.getenv("FRONTEND_URL"):
    frontend_urls.append(os.getenv("FRONTEND_URL"))
if os.getenv("FRONTEND_URL_8081"):
    frontend_urls.append(os.getenv("FRONTEND_URL_8081"))

# Default to allow localhost for development if no env vars set
if not frontend_urls:
    frontend_urls = ["http://localhost:8080", "http://localhost:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_urls,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes under /auth
app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])

# Include SAP intake routes (public endpoints)
from app.sap import routes as sap_routes
app.include_router(sap_routes.router, tags=["Intake"])

# Include SAP dashboard routes (protected endpoints)
from app.sap import dashboard_routes as sap_dashboard_routes
app.include_router(sap_dashboard_routes.router, tags=["Dashboard"])

# Include external integration routes
from app.integration import routes as integration_routes
app.include_router(integration_routes.router, tags=["Integration"])

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "API running successfully"}


@app.on_event("startup")
def on_startup() -> None:
    # Initialize tables on startup, but don't crash service if DB is unavailable
    try:
        from sqlalchemy import text
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized successfully")
        
        # Add student_name column if it doesn't exist (migration)
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE dashboard_records 
                    ADD COLUMN IF NOT EXISTS student_name VARCHAR(200);
                """))
                conn.commit()
                print("✅ student_name column added/verified successfully")
        except Exception as col_exc:
            # Column might already exist or there's a permission issue - that's okay
            print(f"Note: student_name column check: {col_exc}")

        # Add role/district/school columns to users table if missing (migration)
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS role VARCHAR(100);
                """))
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS district_id INTEGER;
                """))
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS school_id INTEGER;
                """))
                conn.commit()
                print("✅ users.role/district_id/school_id columns added/verified successfully")
        except Exception as col_exc:
            print(f"Note: users columns check: {col_exc}")
    except Exception as exc:
        # Log and continue so health checks still pass
        print(f"Startup DB init skipped: {exc}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
