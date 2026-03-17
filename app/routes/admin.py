from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import FlightCreate, FlightStatusUpdate, AnnouncementCreate, AirportOut, AirplaneOut
from app.services.flight_service import create_flight, update_flight_status, create_announcement
from app.auth import get_current_user, require_admin
from app.models import Airport, Airplane

router = APIRouter(prefix="/admin", tags=["Admin"])

# ──────────────────────────────────────────────────────
#  Flights
# ──────────────────────────────────────────────────────

@router.post("/flights", dependencies=[Depends(require_admin)])
def create_new_flight(payload: FlightCreate, db: Session = Depends(get_db)):
    return create_flight(payload, db)

@router.patch("/flights/{id}/status", dependencies=[Depends(require_admin)])
def change_flight_status(id: int, payload: FlightStatusUpdate, db: Session = Depends(get_db)):
    return update_flight_status(id, payload.status, db)

# ──────────────────────────────────────────────────────
#  Announcements
# ──────────────────────────────────────────────────────

@router.post("/announcements", dependencies=[Depends(require_admin)])
def publish_announcement(payload: AnnouncementCreate, db: Session = Depends(get_db)):
    return create_announcement(payload, db)

# ──────────────────────────────────────────────────────
#  Bookings
# ──────────────────────────────────────────────────────

@router.get("/bookings", dependencies=[Depends(require_admin)])
def list_all_bookings(db: Session = Depends(get_db)):
    # Placeholder for booking listing logic
    return {"message": "List of all bookings"}

# ──────────────────────────────────────────────────────
#  Support Data (for admin panel)
# ──────────────────────────────────────────────────────

@router.get("/airports", response_model=list[AirportOut])
def get_all_airports(db: Session = Depends(get_db)):
    """Get all airports for flight creation form"""
    airports = db.query(Airport).all()
    return airports

@router.get("/airplanes", response_model=list[AirplaneOut])
def get_all_airplanes(db: Session = Depends(get_db)):
    """Get all airplanes for flight creation form"""
    airplanes = db.query(Airplane).all()
    return airplanes