"""
routes/tickets.py — Ticket-level endpoints
───────────────────────────────────────────
POST /tickets/{ticket_id}/checkin         – check in a passenger
GET  /tickets/{ticket_id}/boarding-pass   – retrieve boarding pass data
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Booking, BookingStatus, CheckIn, Ticket, User, UserRole
from ..schemas import BoardingPassOut, CheckInOut

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# ──────────────────────────────────────────────────────
#  Helper: load ticket (owner or staff)
# ──────────────────────────────────────────────────────

def _get_ticket_for_user(
    ticket_id: int,
    current_user: User,
    db: Session,
) -> Ticket:
    """Return the Ticket or raise 404/403."""
    ticket: Ticket | None = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    booking: Booking = ticket.booking
    if (
        current_user.role == UserRole.passenger
        and booking.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return ticket


# ──────────────────────────────────────────────────────
#  POST /tickets/{ticket_id}/checkin
# ──────────────────────────────────────────────────────

@router.post(
    "/{ticket_id}/checkin",
    response_model=CheckInOut,
    status_code=status.HTTP_201_CREATED,
    summary="Check in a passenger for their flight",
)
def checkin_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckInOut:
    """
    Creates a CheckIn record for the given ticket.

    Rules:
    - Booking must be CONFIRMED (paid).
    - Ticket must not already be checked in.
    """
    ticket = _get_ticket_for_user(ticket_id, current_user, db)
    booking: Booking = ticket.booking

    if booking.status != BookingStatus.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-in is only available for confirmed (paid) bookings.",
        )

    if ticket.checkin is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This ticket is already checked in.",
        )

    checkin = CheckIn(ticket_id=ticket.id)
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


# ──────────────────────────────────────────────────────
#  GET /tickets/{ticket_id}/boarding-pass
# ──────────────────────────────────────────────────────

@router.get(
    "/{ticket_id}/boarding-pass",
    response_model=BoardingPassOut,
    summary="Get boarding pass data for a checked-in ticket",
)
def get_boarding_pass(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BoardingPassOut:
    """
    Returns boarding pass information including the QR payload.
    Ticket must belong to a CONFIRMED booking.
    """
    ticket = _get_ticket_for_user(ticket_id, current_user, db)
    booking: Booking = ticket.booking
    flight = booking.flight

    if booking.status != BookingStatus.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Boarding pass is only available for confirmed bookings.",
        )

    return BoardingPassOut(
        ticket_id=ticket.id,
        pnr=booking.pnr,
        flight_number=flight.flight_number,
        departure=flight.departure_airport.iata_code,
        arrival=flight.arrival_airport.iata_code,
        departure_time=flight.departure_time,
        seat_number=ticket.seat_number,
        category=ticket.category,
        passenger_name=ticket.passenger_name,
        passport_number=ticket.passport_number,
        qr_data=ticket.qr_data,
        checked_in=ticket.checkin is not None,
    )
