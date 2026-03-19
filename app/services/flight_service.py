# Flight service logic for searching flights and seat maps.

from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models import Airport, Flight, Announcement, FlightStatus
from ..schemas import TicketCategory, FlightCreate, AnnouncementCreate
from datetime import date

def search_flights_service(from_iata: str, to_iata: str, departure_date: date, category: TicketCategory, db: Session):
    dep_airport = db.query(Airport).filter(Airport.iata_code == from_iata.upper()).first()
    arr_airport = db.query(Airport).filter(Airport.iata_code == to_iata.upper()).first()

    if not dep_airport or not arr_airport:
        return None, f"Airport not found: {from_iata if not dep_airport else to_iata}"

    # Map category to the appropriate price column
    category_price_map = {
        TicketCategory.standard: Flight.price_economy,
        TicketCategory.extra_legroom: Flight.price_extra_legroom,
        TicketCategory.business: Flight.price_business,
        TicketCategory.first: Flight.price_first,
    }
    
    price_col = category_price_map[category]

    flights = (
        db.query(Flight)
        .filter(
            Flight.departure_airport_id == dep_airport.id,
            Flight.arrival_airport_id == arr_airport.id,
            Flight.is_active == True,
            Flight.available_seats > 0,
            price_col != None,
        )
        .all()
    )

    # Filter by departure date
    results = [f for f in flights if f.departure_time.date() == departure_date]
    return results, None

def create_flight(payload: FlightCreate, db: Session):
    """Create a new flight."""
    flight = Flight(**payload.dict())
    db.add(flight)
    db.commit()
    db.refresh(flight)
    return flight

def update_flight_status(flight_id: int, status: FlightStatus, db: Session):
    """Update the status of a flight."""
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not flight:
        return None
    flight.status = status
    db.commit()
    db.refresh(flight)
    return flight

def create_announcement(payload: AnnouncementCreate, db: Session):
    """Create an announcement for a flight."""
    data = payload.dict()
    data["body"] = data.pop("message", None)
    announcement = Announcement(**data)
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement