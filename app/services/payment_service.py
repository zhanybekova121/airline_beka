"""
services/payment_service.py — Business logic for payment processing
──────────────────────────────────────────────────────────────────────
process_payment():  find/update existing Payment record (created by booking_service),
                    update booking to CONFIRMED, update ticket seat if specified.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..models import (
    Booking,
    BookingStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    User,
)


def process_payment(
    booking_id: int,
    method: PaymentMethod,
    current_user: User,
    db: Session,
) -> Tuple[Optional[Payment], Optional[str]]:
    """
    Process payment for a booking.
    booking_service already creates a pending Payment — we update it here.

    Returns:
        (Payment, None)  on success
        (None, error_message)  on failure
    """
    booking: Optional[Booking] = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.user_id == current_user.id)
        .first()
    )

    if not booking:
        return None, "Booking not found"

    if booking.status == BookingStatus.cancelled:
        return None, "Booking has been cancelled"

    if booking.status == BookingStatus.confirmed:
        # Already paid — return the existing payment
        if booking.payment:
            return booking.payment, None
        return None, "Booking is already confirmed but no payment record found"

    # Check hold time hasn't expired
    if booking.hold_until:
        now = datetime.now(tz=timezone.utc)
        hold = booking.hold_until
        if hold.tzinfo is None:
            hold = hold.replace(tzinfo=timezone.utc)
        if now > hold:
            booking.status = BookingStatus.cancelled
            db.commit()
            return None, "Booking hold has expired. Please search again."

    # Update the existing pending Payment record (created by booking_service)
    payment: Optional[Payment] = booking.payment
    if payment is None:
        # Safety fallback: create one if missing
        from ..models import TicketCategory
        flight = booking.flight
        category = TicketCategory.standard
        if booking.tickets:
            category = booking.tickets[0].category
        price_map = {
            TicketCategory.standard:      flight.price_economy,
            TicketCategory.extra_legroom: flight.price_extra_legroom or flight.price_economy,
            TicketCategory.business:      flight.price_business or flight.price_economy,
            TicketCategory.first:         flight.price_first or flight.price_economy,
        }
        amount = price_map.get(category, flight.price_economy)
        payment = Payment(
            booking_id=booking.id,
            amount=amount,
            currency="USD",
        )
        db.add(payment)

    # Mark as paid
    payment.method = method
    payment.status = PaymentStatus.paid
    payment.transaction_id = str(uuid.uuid4())
    payment.paid_at = datetime.now(tz=timezone.utc)

    # Confirm the booking
    booking.status = BookingStatus.confirmed
    booking.confirmed_at = datetime.now(tz=timezone.utc)

    db.commit()
    db.refresh(payment)
    return payment, None