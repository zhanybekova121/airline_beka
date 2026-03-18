"""
ORM Models for the Airline System
──────────────────────────────────────────────────────
Entities:
  User & PassengerProfile  – 1-to-1 (passenger personal data)
  Airport                  – IATA code, city, country
  Airplane                 – model, seat map
  Flight                   – route, schedule, status, price
  Booking                  – PNR, hold timer, status
  Ticket                   – seat number, category, QR payload
  Payment                  – amount, method, status
  CheckIn                  – check-in record tied to a Ticket
  Announcement             – flight feed announcement
"""

import enum
import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum,
    Float, ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# ══════════════════════════════════════════════════
#  Enums
# ══════════════════════════════════════════════════

class UserRole(str, enum.Enum):
    passenger = "passenger"
    staff     = "staff"
    admin     = "admin"


class FlightStatus(str, enum.Enum):
    scheduled  = "SCHEDULED"
    boarding   = "BOARDING"
    departed   = "DEPARTED"
    arrived    = "ARRIVED"
    delayed    = "DELAYED"
    cancelled  = "CANCELLED"


class BookingStatus(str, enum.Enum):
    created    = "CREATED"      # held for 10 minutes
    confirmed  = "CONFIRMED"    # payment received
    cancelled  = "CANCELLED"


class TicketCategory(str, enum.Enum):
    standard      = "standard"
    extra_legroom = "extra_legroom"
    business      = "business"
    first         = "first"


class PaymentStatus(str, enum.Enum):
    pending  = "PENDING"
    paid     = "PAID"
    failed   = "FAILED"
    refunded = "REFUNDED"


class PaymentMethod(str, enum.Enum):
    card       = "CARD"
    apple_pay  = "APPLE_PAY"
    google_pay = "GOOGLE_PAY"
    cash       = "CASH"


class AnnouncementType(str, enum.Enum):
    delay        = "DELAY"
    cancellation = "CANCELLATION"
    gate_change  = "GATE_CHANGE"
    boarding     = "BOARDING"
    general      = "GENERAL"


# ══════════════════════════════════════════════════
#  User
# ══════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password  = Column(String, nullable=False)
    full_name        = Column(String(255), nullable=False)
    role             = Column(SAEnum(UserRole), default=UserRole.passenger, nullable=False)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    profile          = relationship(
        "PassengerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    bookings         = relationship("Booking", back_populates="user")


# ══════════════════════════════════════════════════
#  PassengerProfile  (1-to-1 with User)
# ══════════════════════════════════════════════════

class PassengerProfile(Base):
    __tablename__ = "passenger_profiles"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                              unique=True, nullable=False)

    # Personal data
    first_name       = Column(String(100), nullable=True)
    last_name        = Column(String(100), nullable=True)
    phone            = Column(String(30),  nullable=True)
    date_of_birth    = Column(String(10),  nullable=True)   # ISO: YYYY-MM-DD

    # Travel document
    passport_number  = Column(String(50),  nullable=True)
    passport_expiry  = Column(String(10),  nullable=True)   # ISO: YYYY-MM-DD
    nationality      = Column(String(100), nullable=True)

    user             = relationship("User", back_populates="profile")


# ══════════════════════════════════════════════════
#  Airport
# ══════════════════════════════════════════════════

class Airport(Base):
    __tablename__ = "airports"

    id               = Column(Integer, primary_key=True, index=True)
    iata_code        = Column(String(3),  unique=True, index=True, nullable=False)
    icao_code        = Column(String(4),  unique=True, nullable=True)
    name             = Column(String(255), nullable=False)
    city             = Column(String(100), nullable=False)
    country          = Column(String(100), nullable=False)
    timezone         = Column(String(60),  nullable=True)   # e.g. "Asia/Almaty"

    departures       = relationship("Flight", foreign_keys="Flight.departure_airport_id",
                                    back_populates="departure_airport")
    arrivals         = relationship("Flight", foreign_keys="Flight.arrival_airport_id",
                                    back_populates="arrival_airport")


# ══════════════════════════════════════════════════
#  Airplane
# ══════════════════════════════════════════════════

class Airplane(Base):
    """
    Represents a specific aircraft registration.
    `seat_map` is stored as JSON:
      {
        "A1": {"category": "business",      "available": true},
        "B4": {"category": "extra_legroom", "available": false},
        ...
      }
    """
    __tablename__ = "airplanes"

    id               = Column(Integer, primary_key=True, index=True)
    registration     = Column(String(20), unique=True, nullable=False)   # e.g. "UP-B3701"
    model            = Column(String(100), nullable=False)               # e.g. "Boeing 737-800"
    manufacturer     = Column(String(100), nullable=True)
    total_seats      = Column(Integer, nullable=False)
    economy_seats    = Column(Integer, default=0)
    business_seats   = Column(Integer, default=0)
    first_seats      = Column(Integer, default=0)
    seat_map         = Column(JSON, nullable=True)   # full interactive seat map

    flights          = relationship("Flight", back_populates="airplane")


# ══════════════════════════════════════════════════
#  Flight
# ══════════════════════════════════════════════════

class Flight(Base):
    __tablename__ = "flights"

    id                   = Column(Integer, primary_key=True, index=True)
    flight_number        = Column(String(10), unique=True, index=True, nullable=False)
    departure_airport_id = Column(Integer, ForeignKey("airports.id"), nullable=False)
    arrival_airport_id   = Column(Integer, ForeignKey("airports.id"), nullable=False)
    airplane_id          = Column(Integer, ForeignKey("airplanes.id"), nullable=False)

    departure_time       = Column(DateTime(timezone=True), nullable=False)
    arrival_time         = Column(DateTime(timezone=True), nullable=False)

    status               = Column(SAEnum(FlightStatus),
                                  default=FlightStatus.scheduled, nullable=False)

    # Pricing per category
    price_economy        = Column(Float, nullable=False)
    price_extra_legroom  = Column(Float, nullable=True)
    price_business       = Column(Float, nullable=True)
    price_first          = Column(Float, nullable=True)

    available_seats      = Column(Integer, default=0)
    is_active            = Column(Boolean, default=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    departure_airport    = relationship("Airport", foreign_keys=[departure_airport_id],
                                        back_populates="departures")
    arrival_airport      = relationship("Airport", foreign_keys=[arrival_airport_id],
                                        back_populates="arrivals")
    airplane             = relationship("Airplane", back_populates="flights")
    bookings             = relationship("Booking", back_populates="flight")
    announcements        = relationship("Announcement", back_populates="flight",
                                        order_by="Announcement.created_at.desc()")


# ══════════════════════════════════════════════════
#  Booking
# ══════════════════════════════════════════════════

def _generate_pnr() -> str:
    """Random 6-character alphanumeric PNR code."""
    return uuid.uuid4().hex[:6].upper()


class Booking(Base):
    """
    A booking is created in `CREATED` status and held for 10 minutes.
    It transitions to `CONFIRMED` once payment succeeds, or `CANCELLED`
    if the hold expires or the user cancels.
    """
    __tablename__ = "bookings"

    id               = Column(Integer, primary_key=True, index=True)
    pnr              = Column(String(6), unique=True, index=True,
                              default=_generate_pnr, nullable=False)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    flight_id        = Column(Integer, ForeignKey("flights.id"), nullable=False)

    status           = Column(SAEnum(BookingStatus),
                              default=BookingStatus.created, nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    # hold_until = created_at + 10 min; enforced at application level
    hold_until       = Column(DateTime(timezone=True), nullable=True)
    confirmed_at     = Column(DateTime(timezone=True), nullable=True)
    cancelled_at     = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user             = relationship("User", back_populates="bookings")
    flight           = relationship("Flight", back_populates="bookings")
    tickets          = relationship("Ticket", back_populates="booking",
                                    cascade="all, delete-orphan")
    payment          = relationship("Payment", back_populates="booking",
                                    uselist=False, cascade="all, delete-orphan")


# ══════════════════════════════════════════════════
#  Ticket
# ══════════════════════════════════════════════════

class Ticket(Base):
    __tablename__ = "tickets"

    id               = Column(Integer, primary_key=True, index=True)
    booking_id       = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"),
                              nullable=False)
    seat_number      = Column(String(5),  nullable=False)   # e.g. "12A"
    category         = Column(SAEnum(TicketCategory),
                              default=TicketCategory.standard, nullable=False)

    # Passenger info snapshot (denormalised for the ticket PDF)
    passenger_name   = Column(String(255), nullable=True)
    passport_number  = Column(String(50),  nullable=True)

    # QR payload – JSON string that encodes PNR + seat + flight
    qr_data          = Column(Text, nullable=True)
    issued_at        = Column(DateTime(timezone=True), server_default=func.now())

    booking          = relationship("Booking", back_populates="tickets")
    checkin          = relationship("CheckIn", back_populates="ticket",
                                    uselist=False, cascade="all, delete-orphan")


# ══════════════════════════════════════════════════
#  Payment
# ══════════════════════════════════════════════════

class Payment(Base):
    __tablename__ = "payments"

    id               = Column(Integer, primary_key=True, index=True)
    booking_id       = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"),
                              unique=True, nullable=False)

    amount           = Column(Float, nullable=False)
    currency         = Column(String(3), default="USD", nullable=False)
    status           = Column(SAEnum(PaymentStatus),
                              default=PaymentStatus.pending, nullable=False)
    method           = Column(SAEnum(PaymentMethod),
                              default=PaymentMethod.card, nullable=False)

    # External gateway reference (e.g. Stripe charge_id)
    transaction_id   = Column(String(255), nullable=True)
    paid_at          = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    booking          = relationship("Booking", back_populates="payment")


# ══════════════════════════════════════════════════
#  CheckIn
# ══════════════════════════════════════════════════

class CheckIn(Base):
    """
    A check-in record created when a passenger checks in for their flight.
    One per Ticket; only allowed when the parent Booking is CONFIRMED.
    """
    __tablename__ = "checkins"

    id               = Column(Integer, primary_key=True, index=True)
    ticket_id        = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"),
                              unique=True, nullable=False)

    checked_in_at    = Column(DateTime(timezone=True), server_default=func.now())

    ticket           = relationship("Ticket", back_populates="checkin")


# ══════════════════════════════════════════════════
#  Announcement
# ══════════════════════════════════════════════════

class Announcement(Base):
    """
    A message tied to a specific flight (e.g. gate change, delay notice).
    Staff create these; passengers can read them.
    """
    __tablename__ = "announcements"

    id          = Column(Integer, primary_key=True, index=True)
    flight_id   = Column(Integer, ForeignKey("flights.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    type        = Column(SAEnum(AnnouncementType),
                         default=AnnouncementType.general, nullable=False)
    title       = Column(String(200), nullable=False)
    body        = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    flight      = relationship("Flight", back_populates="announcements")
