"""
routes/flights.py — Flight search & seat map endpoints
────────────────────────────────────────────────────────
GET /airports                – get all airports
GET /flights/search          – search available flights
GET /flights/{id}/seats      – get seat map for a specific flight
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Airport, Flight, User
from ..schemas import FlightOut, AirportOut, TicketCategory
from ..services.flight_service import search_flights_service

router = APIRouter(prefix="/flights", tags=["Flights"])


# ──────────────────────────────────────────────────────
#  Airports (public)
# ──────────────────────────────────────────────────────

@router.get(
    "/airports",
    response_model=List[AirportOut],
    summary="Get all airports",
)
def get_airports(db: Session = Depends(get_db)):
    """Return list of all available airports."""
    airports = db.query(Airport).all()
    return airports


# ──────────────────────────────────────────────────────
#  Flight Search
# ──────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=List[FlightOut],
    summary="Search available flights",
)
def search_flights(
    from_iata: str = Query(..., min_length=3, max_length=3),
    to_iata: str = Query(..., min_length=3, max_length=3),
    departure_date: date = Query(...),
    category: TicketCategory = Query(TicketCategory.standard),
    db: Session = Depends(get_db),
):
    results, error = search_flights_service(from_iata, to_iata, departure_date, category, db)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return results


# ──────────────────────────────────────────────────────
#  Seat Map
# ──────────────────────────────────────────────────────

@router.get(
    "/{flight_id}/seats",
    summary="Get seat map for a flight",
)
def get_seat_map(
    flight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Return the airplane's seat map for a given flight.

    The map is a JSON object where each key is a seat label (e.g. `"12A"`)
    and the value contains:
    ```json
    {
      "category": "economy",
      "available": true
    }
    ```
    Seats that are already booked on this flight have `"available": false`.
    """
    flight: Optional[Flight] = db.query(Flight).filter(
        Flight.id == flight_id,
        Flight.is_active == True,
    ).first()

    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found or inactive")

    airplane = flight.airplane
    base_map: dict = airplane.seat_map or {}

    # Mark seats taken by confirmed/created bookings on this flight
    from ..models import Booking, BookingStatus, Ticket
    taken_seats = (
        db.query(Ticket.seat_number)
        .join(Booking, Ticket.booking_id == Booking.id)
        .filter(
            Booking.flight_id == flight_id,
            Booking.status.in_([BookingStatus.created, BookingStatus.confirmed]),
        )
        .all()
    )
    taken_set = {row[0] for row in taken_seats}

    # Overlay availability on the base map
    seat_map = {
        seat: {**info, "available": seat not in taken_set}
        for seat, info in base_map.items()
    }

    return {
        "flight_id":    flight.id,
        "flight_number": flight.flight_number,
        "airplane":     airplane.model,
        "total_seats":  airplane.total_seats,
        "seat_map":     seat_map,
    }


# ──────────────────────────────────────────────────────
#  Announcements (public, requires auth)
# ──────────────────────────────────────────────────────

@router.get(
    "/{flight_id}/announcements",
    summary="Get announcements for a flight",
)
def get_flight_announcements(
    flight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Return all announcements for a given flight, newest first."""
    from ..models import Announcement
    announcements = (
        db.query(Announcement)
        .filter(Announcement.flight_id == flight_id)
        .order_by(Announcement.created_at.desc())
        .all()
    )
    return [
        {
            "id":         a.id,
            "flight_id":  a.flight_id,
            "type":       a.type.value if a.type else "GENERAL",
            "title":      a.title,
            "body":       a.body,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in announcements
    ]
