"""
routes/payments.py — Payment endpoint
──────────────────────────────────────
POST /bookings/{booking_id}/pay  – pay for a booking, generate ticket
GET  /bookings/{booking_id}/pay  – get payment status for a booking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Booking, BookingStatus, PaymentMethod, User
from ..schemas import PaymentOut, PayRequest
from ..services.payment_service import process_payment

router = APIRouter(prefix="/bookings", tags=["Payments"])


@router.post(
    "/{booking_id}/pay",
    response_model=PaymentOut,
    summary="Pay for a booking",
)
def pay_booking(
    booking_id: int,
    payload: PayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentOut:
    """
    Process payment for a booking.
    - Validates the booking belongs to current user and hold hasn't expired
    - Creates a Payment record
    - Confirms the booking (status → CONFIRMED)
    - Generates a Ticket for the passenger
    """
    payment, error = process_payment(
        booking_id=booking_id,
        method=payload.method,
        current_user=current_user,
        db=db,
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error,
        )
    return payment


@router.get(
    "/{booking_id}/pay",
    response_model=PaymentOut,
    summary="Get payment info for a booking",
)
def get_payment(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentOut:
    """Return payment details for a given booking."""
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.user_id == current_user.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.payment is None:
        raise HTTPException(status_code=404, detail="No payment found for this booking")
    return booking.payment
