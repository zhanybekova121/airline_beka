"""
routes/bookings.py — Booking creation & management
────────────────────────────────────────────────────
POST /bookings           – create booking with 10-min hold + PNR
GET  /bookings/my        – list current user's bookings
GET  /bookings/{pnr}     – get booking by PNR code
DELETE /bookings/{pnr}   – cancel a booking
"""

import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import (
    Booking,
    BookingStatus,
    Flight,
    Payment,
    PaymentStatus,
    PaymentMethod,
    PassengerProfile,
    Ticket,
    TicketCategory,
    User,
    UserRole,
)
from ..schemas import BookingCreate, BookingOut
from ..services.booking_service import create_booking_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])

HOLD_MINUTES = 10  # booking is held for this many minutes before auto-expiry


# ──────────────────────────────────────────────────────
#  Helper: price selector
# ──────────────────────────────────────────────────────

def _get_price(flight: Flight, category: TicketCategory) -> float:
    """Return the price for the requested seat category or raise 400."""
    price_map = {
        TicketCategory.standard:      flight.price_economy,
        TicketCategory.extra_legroom: flight.price_extra_legroom,
        TicketCategory.business:      flight.price_business,
        TicketCategory.first:         flight.price_first,
    }
    price = price_map.get(category)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seat category '{category}' is not available on this flight",
        )
    return price


# ──────────────────────────────────────────────────────
#  Helper: QR payload
# ──────────────────────────────────────────────────────

def _build_qr_data(booking: Booking, seat_number: str) -> str:
    """Encode essential booking data as a JSON string for QR generation."""
    return json.dumps({
        "pnr":         booking.pnr,
        "flight":      booking.flight.flight_number,
        "seat":        seat_number,
        "passenger":   booking.user.full_name,
        "departure":   booking.flight.departure_time.isoformat(),
    })


# ──────────────────────────────────────────────────────
#  CREATE booking  (10-min hold)
# ──────────────────────────────────────────────────────

@router.post(
    "",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a booking with 10-minute seat hold",
)
def create_booking(
    payload: BookingCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking, error = create_booking_service(payload, current_user, db)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return booking


# ──────────────────────────────────────────────────────
#  LIST my bookings
# ──────────────────────────────────────────────────────

@router.get(
    "/my",
    response_model=List[BookingOut],
    summary="List all bookings of current user",
)
def my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[BookingOut]:
    """Return all bookings for the currently authenticated user, newest first."""
    return (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


# ──────────────────────────────────────────────────────
#  GET by PNR
# ──────────────────────────────────────────────────────

@router.get(
    "/{pnr}",
    response_model=BookingOut,
    summary="Get booking by PNR code",
)
def get_booking_by_pnr(
    pnr: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookingOut:
    """
    Retrieve a booking by its 6-character PNR code.
    Passengers can only access their own bookings; staff can access any.
    """
    booking: Booking = db.query(Booking).filter(
        Booking.pnr == pnr.upper()
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking PNR '{pnr}' not found")

    # Passengers can only see their own bookings
    if (
        current_user.role == UserRole.passenger
        and booking.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return booking


# ──────────────────────────────────────────────────────
#  CANCEL booking
# ──────────────────────────────────────────────────────

@router.delete(
    "/{pnr}",
    status_code=status.HTTP_200_OK,
    summary="Cancel a booking by PNR",
)
def cancel_booking(
    pnr: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Cancel a booking. Refunds available seats back to the flight.
    Only the owner or staff may cancel.
    """
    booking: Booking = db.query(Booking).filter(
        Booking.pnr == pnr.upper()
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking '{pnr}' not found")
    if (
        current_user.role == UserRole.passenger
        and booking.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    if booking.status == BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    # ── 24-hour cancellation rule ──────────────────────────────────
    departure = booking.flight.departure_time
    now = datetime.now(tz=timezone.utc)
    # Make departure tz-aware if stored without tzinfo
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    hours_until_departure = (departure - now).total_seconds() / 3600
    if hours_until_departure < 24:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot cancel: departure is in "
                f"{int(hours_until_departure)}h "
                f"{int((hours_until_departure % 1) * 60)}m. "
                "Cancellations must be made at least 24 hours before departure."
            ),
        )
    # ──────────────────────────────────────────────────────────────

    booking.status = BookingStatus.cancelled
    booking.cancelled_at = datetime.now(tz=timezone.utc)
    booking.flight.available_seats += 1  # release seat

    # Mark payment as refunded if it was paid
    if booking.payment and booking.payment.status == PaymentStatus.paid:
        booking.payment.status = PaymentStatus.refunded

    db.commit()
    return {"detail": f"Booking {pnr} successfully cancelled"}
