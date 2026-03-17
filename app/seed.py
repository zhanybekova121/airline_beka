"""
seed.py — Initial database population
──────────────────────────────────────
seed_db() is called once at application startup.
It checks each table: if empty → inserts reference data.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import Airplane, Airport, Flight, FlightStatus, User, UserRole


def seed_db(db: Session) -> None:
    """Populate empty tables with reference data and a test staff user."""
    _seed_airports(db)
    _seed_airplanes(db)
    _seed_admin_user(db)
    _seed_flights(db)


# ──────────────────────────────────────────────────────

def _seed_airports(db: Session) -> None:
    if db.query(Airport).count():
        return
    db.add_all([
        Airport(iata_code="ALA", icao_code="UAAA",
                name="Almaty International Airport",
                city="Almaty",   country="Kazakhstan",     timezone="Asia/Almaty"),
        Airport(iata_code="IST", icao_code="LTFM",
                name="Istanbul Airport",
                city="Istanbul", country="Turkey",         timezone="Europe/Istanbul"),
        Airport(iata_code="JFK", icao_code="KJFK",
                name="John F. Kennedy International",
                city="New York", country="USA",            timezone="America/New_York"),
        Airport(iata_code="DXB", icao_code="OMDB",
                name="Dubai International Airport",
                city="Dubai",    country="UAE",            timezone="Asia/Dubai"),
        Airport(iata_code="LHR", icao_code="EGLL",
                name="Heathrow Airport",
                city="London",   country="United Kingdom", timezone="Europe/London"),
    ])
    db.commit()
    print("✅  Airports seeded  (ALA, IST, JFK, DXB, LHR)")


def _seed_airplanes(db: Session) -> None:
    if db.query(Airplane).count():
        return
    db.add_all([
        Airplane(
            registration="UP-B3701", model="737-800", manufacturer="Boeing",
            total_seats=162, economy_seats=138, business_seats=24, first_seats=0,
            seat_map={},
        ),
        Airplane(
            registration="UP-A3210", model="A321neo", manufacturer="Airbus",
            total_seats=194, economy_seats=165, business_seats=25, first_seats=4,
            seat_map={},
        ),
        Airplane(
            registration="UP-B7890", model="787-9 Dreamliner", manufacturer="Boeing",
            total_seats=296, economy_seats=232, business_seats=48, first_seats=16,
            seat_map={},
        ),
    ])
    db.commit()
    print("✅  Airplanes seeded  (737-800, A321neo, 787-9)")


def _seed_flights(db: Session) -> None:
    """Create sample flights for the next 7 days so search always finds results."""
    if db.query(Flight).count():
        return

    # Get airports and airplanes
    ala = db.query(Airport).filter(Airport.iata_code == "ALA").first()
    ist = db.query(Airport).filter(Airport.iata_code == "IST").first()
    jfk = db.query(Airport).filter(Airport.iata_code == "JFK").first()
    dxb = db.query(Airport).filter(Airport.iata_code == "DXB").first()
    lhr = db.query(Airport).filter(Airport.iata_code == "LHR").first()

    plane1 = db.query(Airplane).filter(Airplane.registration == "UP-B3701").first()
    plane2 = db.query(Airplane).filter(Airplane.registration == "UP-A3210").first()
    plane3 = db.query(Airplane).filter(Airplane.registration == "UP-B7890").first()

    flights = []

    # Create flights for today + next 6 days (7 days total)
    for day_offset in range(7):
        base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)

        # ALA → IST  (5h flight, departs 08:00)
        flights.append(Flight(
            flight_number=f"AK10{day_offset + 1}",
            departure_airport_id=ala.id,
            arrival_airport_id=ist.id,
            airplane_id=plane1.id,
            departure_time=base + timedelta(hours=8),
            arrival_time=base + timedelta(hours=13),
            status=FlightStatus.scheduled,
            price_economy=150.0,
            price_extra_legroom=200.0,
            price_business=400.0,
            available_seats=100,
            is_active=True,
        ))

        # ALA → DXB  (5h flight, departs 09:00)
        flights.append(Flight(
            flight_number=f"AK20{day_offset + 1}",
            departure_airport_id=ala.id,
            arrival_airport_id=dxb.id,
            airplane_id=plane2.id,
            departure_time=base + timedelta(hours=9),
            arrival_time=base + timedelta(hours=14),
            status=FlightStatus.scheduled,
            price_economy=250.0,
            price_extra_legroom=320.0,
            price_business=550.0,
            available_seats=110,
            is_active=True,
        ))

        # DXB → ALA  (5h flight, departs 15:00)
        flights.append(Flight(
            flight_number=f"AK30{day_offset + 1}",
            departure_airport_id=dxb.id,
            arrival_airport_id=ala.id,
            airplane_id=plane1.id,
            departure_time=base + timedelta(hours=15),
            arrival_time=base + timedelta(hours=20),
            status=FlightStatus.scheduled,
            price_economy=220.0,
            price_extra_legroom=280.0,
            price_business=480.0,
            available_seats=90,
            is_active=True,
        ))

        # IST → JFK  (10h flight, departs 12:00)
        flights.append(Flight(
            flight_number=f"AK40{day_offset + 1}",
            departure_airport_id=ist.id,
            arrival_airport_id=jfk.id,
            airplane_id=plane3.id,
            departure_time=base + timedelta(hours=12),
            arrival_time=base + timedelta(hours=22),
            status=FlightStatus.scheduled,
            price_economy=320.0,
            price_extra_legroom=400.0,
            price_business=700.0,
            price_first=1200.0,
            available_seats=180,
            is_active=True,
        ))

        # LHR → ALA  (7h flight, departs 11:00)
        flights.append(Flight(
            flight_number=f"AK50{day_offset + 1}",
            departure_airport_id=lhr.id,
            arrival_airport_id=ala.id,
            airplane_id=plane2.id,
            departure_time=base + timedelta(hours=11),
            arrival_time=base + timedelta(hours=18),
            status=FlightStatus.scheduled,
            price_economy=280.0,
            price_extra_legroom=350.0,
            price_business=600.0,
            price_first=1000.0,
            available_seats=130,
            is_active=True,
        ))

    db.add_all(flights)
    db.commit()
    print(f"✅  Flights seeded  ({len(flights)} flights for next 7 days)")


def _seed_staff_user(db: Session) -> None:
    if db.query(User).filter(User.email == "staff@airline.com").first():
        return
    db.add(User(
        email="staff@airline.com",
        hashed_password=hash_password("staff1234"),
        full_name="Test Staff User",
        role=UserRole.staff,
        is_active=True,
    ))
    db.commit()
    print("✅  Staff user seeded  →  staff@airline.com / staff1234")


def _seed_admin_user(db: Session) -> None:
    """Create a test admin user."""
    if db.query(User).filter(User.email == "admin@airline.com").first():
        return
    db.add(User(
        email="admin@airline.com",
        hashed_password=hash_password("admin1234"),
        full_name="Admin User",
        role=UserRole.admin,
        is_active=True,
    ))
    db.commit()
    print("✅  Admin user seeded  →  admin@airline.com / admin1234")
