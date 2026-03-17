"""
Pydantic schemas for request validation and response serialization.
One Base + Create + Out pattern per entity.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ══════════════════════════════════════════════════
#  Enums  (mirror models.py)
# ══════════════════════════════════════════════════

class UserRole(str, Enum):
    passenger = "passenger"
    staff     = "staff"
    admin     = "admin"


class FlightStatus(str, Enum):
    scheduled = "SCHEDULED"
    boarding  = "BOARDING"
    departed  = "DEPARTED"
    arrived   = "ARRIVED"
    delayed   = "DELAYED"
    cancelled = "CANCELLED"


class BookingStatus(str, Enum):
    created   = "CREATED"
    confirmed = "CONFIRMED"
    cancelled = "CANCELLED"


class TicketCategory(str, Enum):
    standard      = "standard"
    extra_legroom = "extra_legroom"
    business      = "business"
    first         = "first"


class PaymentStatus(str, Enum):
    pending  = "PENDING"
    paid     = "PAID"
    failed   = "FAILED"
    refunded = "REFUNDED"


class PaymentMethod(str, Enum):
    card       = "CARD"
    apple_pay  = "APPLE_PAY"
    google_pay = "GOOGLE_PAY"
    cash       = "CASH"


# ══════════════════════════════════════════════════
#  Auth
# ══════════════════════════════════════════════════

class UserRegister(BaseModel):
    email:     EmailStr
    password:  str = Field(..., min_length=6, description="At least 6 characters")
    full_name: str = Field(..., min_length=2)


class UserLogin(BaseModel):
    email:    EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ══════════════════════════════════════════════════
#  User
# ══════════════════════════════════════════════════

class UserOut(BaseModel):
    id:         int
    email:      str
    full_name:  str
    role:       UserRole
    is_active:  bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════
#  PassengerProfile
# ══════════════════════════════════════════════════

class PassengerProfileUpdate(BaseModel):
    first_name:      Optional[str] = Field(None, max_length=100)
    last_name:       Optional[str] = Field(None, max_length=100)
    phone:           Optional[str] = Field(None, max_length=30)
    date_of_birth:   Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    passport_number: Optional[str] = Field(None, max_length=50)
    passport_expiry: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    nationality:     Optional[str] = Field(None, max_length=100)


class PassengerProfileOut(BaseModel):
    id:              int
    user_id:         int
    first_name:      Optional[str] = None
    last_name:       Optional[str] = None
    phone:           Optional[str] = None
    date_of_birth:   Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[str] = None
    nationality:     Optional[str] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════
#  Airport
# ══════════════════════════════════════════════════

class AirportCreate(BaseModel):
    iata_code: str = Field(..., min_length=3, max_length=3)
    icao_code: Optional[str] = Field(None, max_length=4)
    name:      str
    city:      str
    country:   str
    timezone:  Optional[str] = None


class AirportOut(BaseModel):
    id:        int
    iata_code: str
    icao_code: Optional[str] = None
    name:      str
    city:      str
    country:   str
    timezone:  Optional[str] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════
#  Airplane
# ══════════════════════════════════════════════════

class AirplaneCreate(BaseModel):
    registration:  str = Field(..., max_length=20)
    model:         str
    manufacturer:  Optional[str] = None
    total_seats:   int = Field(..., gt=0)
    economy_seats: int = Field(0, ge=0)
    business_seats: int = Field(0, ge=0)
    first_seats:   int = Field(0, ge=0)
    seat_map:      Optional[Dict[str, Any]] = None


class AirplaneOut(BaseModel):
    id:             int
    registration:   str
    model:          str
    manufacturer:   Optional[str] = None
    total_seats:    int
    economy_seats:  int
    business_seats: int
    first_seats:    int
    seat_map:       Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════
#  Flight
# ══════════════════════════════════════════════════

class FlightCreate(BaseModel):
    flight_number:        str = Field(..., max_length=10)
    departure_airport_id: int
    arrival_airport_id:   int
    airplane_id:          int
    departure_time:       datetime
    arrival_time:         datetime
    price_economy:        float = Field(..., gt=0)
    price_extra_legroom:  Optional[float] = None
    price_business:       Optional[float] = None
    price_first:          Optional[float] = None
    available_seats:      int = Field(0, ge=0)


class FlightOut(BaseModel):
    id:                  int
    flight_number:       str
    departure_airport:   AirportOut
    arrival_airport:     AirportOut
    airplane:            AirplaneOut
    departure_time:      datetime
    arrival_time:        datetime
    status:              FlightStatus
    price_economy:       float
    price_extra_legroom: Optional[float] = None
    price_business:      Optional[float] = None
    price_first:         Optional[float] = None
    available_seats:     int
    is_active:           bool

    model_config = {"from_attributes": True}


class FlightSearch(BaseModel):
    from_iata:      str = Field(..., min_length=3, max_length=3)
    to_iata:        str = Field(..., min_length=3, max_length=3)
    departure_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    category:       TicketCategory = TicketCategory.standard


class FlightStatusUpdate(BaseModel):
    flight_id: int
    status: FlightStatus


# ══════════════════════════════════════════════════
#  Payment  (declared before Booking for forward ref)
# ══════════════════════════════════════════════════

class PayRequest(BaseModel):
    """Body for POST /bookings/{id}/pay."""
    method: PaymentMethod = PaymentMethod.card


class PaymentCreate(BaseModel):
    booking_id: int
    amount:     float = Field(..., gt=0)
    currency:   str   = Field("USD", max_length=3)
    method:     PaymentMethod = PaymentMethod.card


class PaymentOut(BaseModel):
    id:             int
    booking_id:     int
    amount:         float
    currency:       str
    status:         PaymentStatus
    method:         PaymentMethod
    transaction_id: Optional[str] = None
    paid_at:        Optional[datetime] = None
    created_at:     Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════
#  Ticket
# ══════════════════════════════════════════════════

class CheckInOut(BaseModel):
    id:            int
    ticket_id:     int
    checked_in_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnnouncementOut(BaseModel):
    id:         int
    flight_id:  int
    title:      str
    body:       Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnnouncementCreate(BaseModel):
    flight_id: int
    title: str
    body: Optional[str] = None


class TicketOut(BaseModel):
    id:              int
    booking_id:      int
    seat_number:     str
    category:        TicketCategory
    passenger_name:  Optional[str] = None
    passport_number: Optional[str] = None
    qr_data:         Optional[str] = None
    issued_at:       Optional[datetime] = None
    checkin:         Optional[CheckInOut] = None

    model_config = {"from_attributes": True}


class BoardingPassOut(BaseModel):
    """Response model for GET /tickets/{ticket_id}/boarding-pass."""
    ticket_id:       int
    pnr:             str
    flight_number:   str
    departure:       str  # airport IATA
    arrival:         str  # airport IATA
    departure_time:  datetime
    seat_number:     str
    category:        TicketCategory
    passenger_name:  Optional[str] = None
    passport_number: Optional[str] = None
    qr_data:         Optional[str] = None
    checked_in:      bool = False

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════
#  Booking
# ══════════════════════════════════════════════════

class BookingCreate(BaseModel):
    flight_id:   int
    category:    TicketCategory = TicketCategory.standard
    seat_number: Optional[str] = None


class BookingOut(BaseModel):
    id:           int
    pnr:          str
    flight:       FlightOut
    status:       BookingStatus
    hold_until:   Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at:   Optional[datetime] = None
    tickets:      List[TicketOut] = []
    payment:      Optional[PaymentOut] = None

    model_config = {"from_attributes": True}
