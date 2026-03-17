# Booking service logic for creating and managing bookings.

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..models import Booking, Flight, Ticket, Payment, BookingStatus, PaymentStatus, PaymentMethod
from ..schemas import BookingCreate, TicketCategory

def create_booking_service(payload: BookingCreate, current_user, db: Session):
    if current_user.role == "passenger":
        profile = current_user.profile
        if profile is None or not profile.passport_number:
            return None, "Please complete your passenger profile before booking."

    flight = db.query(Flight).filter(Flight.id == payload.flight_id, Flight.is_active == True).first()
    if not flight:
        return None, "Flight not found or inactive."

    if flight.available_seats <= 0:
        return None, "No seats available on this flight."

    total_price = _get_price(flight, payload.category)

    now = datetime.now(tz=timezone.utc)
    booking = Booking(
        user_id=current_user.id,
        flight_id=flight.id,
        status=BookingStatus.created,
        hold_until=now + timedelta(minutes=10),
    )
    db.add(booking)
    db.flush()

    seat_number = payload.seat_number or "TBD"
    ticket = Ticket(
        booking_id=booking.id,
        seat_number=seat_number,
        category=payload.category,
        passenger_name=current_user.full_name,
        passport_number=current_user.profile.passport_number if current_user.profile else None,
    )
    db.add(ticket)

    payment = Payment(
        booking_id=booking.id,
        amount=total_price,
        currency="USD",
        status=PaymentStatus.pending,
        method=PaymentMethod.card,
    )
    db.add(payment)

    flight.available_seats -= 1

    db.commit()
    db.refresh(booking)
    return booking, None

def _get_price(flight: Flight, category: TicketCategory):
    price_map = {
        TicketCategory.standard: flight.price_economy,
        TicketCategory.extra_legroom: flight.price_extra_legroom,
        TicketCategory.business: flight.price_business,
        TicketCategory.first: flight.price_first,
    }
    price = price_map.get(category)
    if price is None:
        raise ValueError(f"Seat category '{category}' is not available on this flight.")
    return price