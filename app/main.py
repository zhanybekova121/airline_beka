"""
main.py — FastAPI application entry point
─────────────────────────────────────────
Only does three things:
  1. Creates the FastAPI app and adds middleware
  2. Includes the APIRouters from app/routes/
  3. Runs seed_db() on startup

All business logic lives in auth.py.
All endpoints live in routes/.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, inspect

from .database import Base, engine, get_db
from .routes import auth as auth_router
from .routes import flights as flights_router
from .routes import bookings as bookings_router
from .routes import payments as payments_router
from .routes import admin as admin_router
from .routes import tickets as tickets_router
from .seed import seed_db

# ──────────────────────────────────────────────────────
#  Application
# ──────────────────────────────────────────────────────

app = FastAPI(
    title="Airline System API",
    version="1.0.0",
    description=(
        "RESTful backend for the airline booking system.\n\n"
        "**Test staff account:** `staff@airline.com` / `staff1234`"
    ),
)

# CORS — allow all origins in development; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────
#  Routers
# ──────────────────────────────────────────────────────

app.include_router(auth_router.router)
app.include_router(flights_router.router)
app.include_router(bookings_router.router)
app.include_router(payments_router.router)
app.include_router(admin_router.router)
app.include_router(tickets_router.router)

# ──────────────────────────────────────────────────────
#  Startup
# ──────────────────────────────────────────────────────

def run_migrations():
    with engine.connect() as conn:
        # Check if 'type' column exists in announcements
        inspector = inspect(engine)
        if 'announcements' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('announcements')]
            
            if 'type' not in columns:
                conn.execute(text(
                    "ALTER TABLE announcements ADD COLUMN type VARCHAR DEFAULT 'general'"
                ))
                conn.commit()
                print("✅ Migration: added 'type' column to announcements table")
            else:
                print("✅ Migration: 'type' column already exists")

@app.on_event("startup")
def on_startup() -> None:
    """Create all DB tables and populate seed data on first launch."""
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = next(get_db())
    try:
        seed_db(db)
    finally:
        db.close()


# ──────────────────────────────────────────────────────
#  Health check
# ──────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root() -> dict:
    return {"status": "ok", "docs": "/docs"}
