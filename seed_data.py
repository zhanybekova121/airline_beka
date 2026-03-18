"""
seed_data.py — Standalone database seed script
───────────────────────────────────────────────
Run from the `backend/` directory:

    python seed_data.py

What it does:
  1. Creates all database tables (safe to run on existing DB).
  2. Creates an admin user  →  admin@airline.com / Admin1234!
  3. Seeds 5 airports        →  IST, JFK, LHR, DXB, FRA
  4. Seeds 3 airplanes
  5. Seeds 10 future SCHEDULED flights with realistic prices.

Everything is idempotent — running multiple times is safe.
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# ── Make the local `app` package importable ──────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal
from app.auth import hash_password
from app.models import Airplane, Airport, Flight, FlightStatus, User, UserRole

# ── Admin credentials ─────────────────────────────────────────────────────────
ADMIN_EMAIL    = "admin@airline.com"
ADMIN_PASSWORD = "Admin1234!"
ADMIN_NAME     = "System Administrator"


# ════════════════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════════════════

def _upsert_admin(db):
    """Return (user, created). created=True when the row was inserted now."""
    user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if user:
        return user, False
    user = User(
        email=ADMIN_EMAIL,
        hashed_password=hash_password(ADMIN_PASSWORD),
        full_name=ADMIN_NAME,
        role=UserRole.admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def _upsert_airports(db):
    """Insert airports that don't exist yet. Returns (airports_dict, new_count)."""
    airport_data = [
        dict(iata_code="IST", icao_code="LTFM",
             name="Istanbul Airport",
             city="Istanbul",  country="Turkey",          timezone="Europe/Istanbul"),
        dict(iata_code="JFK", icao_code="KJFK",
             name="John F. Kennedy International Airport",
             city="New York",  country="USA",             timezone="America/New_York"),
        dict(iata_code="LHR", icao_code="EGLL",
             name="Heathrow Airport",
             city="London",    country="United Kingdom",  timezone="Europe/London"),
        dict(iata_code="DXB", icao_code="OMDB",
             name="Dubai International Airport",
             city="Dubai",     country="UAE",             timezone="Asia/Dubai"),
        dict(iata_code="FRA", icao_code="EDDF",
             name="Frankfurt Airport",
             city="Frankfurt", country="Germany",         timezone="Europe/Berlin"),
    ]
    new_count = 0
    for d in airport_data:
        if not db.query(Airport).filter(Airport.iata_code == d["iata_code"]).first():
            db.add(Airport(**d))
            new_count += 1
    if new_count:
        db.commit()

    codes = [d["iata_code"] for d in airport_data]
    airports = {
        a.iata_code: a
        for a in db.query(Airport).filter(Airport.iata_code.in_(codes)).all()
    }
    return airports, new_count


def _upsert_airplanes(db):
    """Insert airplanes that don't exist yet. Returns (planes_dict, new_count)."""
    plane_data = [
        dict(registration="TC-JFA", model="Boeing 737-800",   manufacturer="Boeing",
             total_seats=162, economy_seats=138, business_seats=24,  first_seats=0,  seat_map={}),
        dict(registration="D-AIWA", model="Airbus A321neo",   manufacturer="Airbus",
             total_seats=194, economy_seats=165, business_seats=25,  first_seats=4,  seat_map={}),
        dict(registration="G-STBA", model="Boeing 787-9",     manufacturer="Boeing",
             total_seats=296, economy_seats=232, business_seats=48,  first_seats=16, seat_map={}),
    ]
    new_count = 0
    for d in plane_data:
        if not db.query(Airplane).filter(Airplane.registration == d["registration"]).first():
            db.add(Airplane(**d))
            new_count += 1
    if new_count:
        db.commit()

    regs = [d["registration"] for d in plane_data]
    planes = {
        a.registration: a
        for a in db.query(Airplane).filter(Airplane.registration.in_(regs)).all()
    }
    return planes, new_count


def _upsert_flights(db, airports, planes):
    """
    Ensure 10 specific future flights exist.
    Returns (total_in_db, newly_inserted).
    """
    now = datetime.now(tz=timezone.utc)

    def base(days):
        return (now + timedelta(days=days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    ist = airports["IST"]
    jfk = airports["JFK"]
    lhr = airports["LHR"]
    dxb = airports["DXB"]
    fra = airports["FRA"]

    b737 = planes["TC-JFA"]
    a321 = planes["D-AIWA"]
    b787 = planes["G-STBA"]

    flight_specs = [
        # IST → LHR  (3h 30m,  day +1, 07:00)
        dict(flight_number="TK1980",
             departure_airport_id=ist.id, arrival_airport_id=lhr.id,
             airplane_id=b737.id,
             departure_time=base(1) + timedelta(hours=7),
             arrival_time  =base(1) + timedelta(hours=10, minutes=30),
             price_economy=199.0, price_extra_legroom=260.0,
             price_business=480.0, price_first=None,
             available_seats=120),

        # LHR → IST  (3h 30m,  day +1, 14:00)
        dict(flight_number="BA0676",
             departure_airport_id=lhr.id, arrival_airport_id=ist.id,
             airplane_id=b737.id,
             departure_time=base(1) + timedelta(hours=14),
             arrival_time  =base(1) + timedelta(hours=17, minutes=30),
             price_economy=210.0, price_extra_legroom=275.0,
             price_business=500.0, price_first=None,
             available_seats=115),

        # IST → JFK  (10h,     day +2, 09:00)
        dict(flight_number="TK0001",
             departure_airport_id=ist.id, arrival_airport_id=jfk.id,
             airplane_id=b787.id,
             departure_time=base(2) + timedelta(hours=9),
             arrival_time  =base(2) + timedelta(hours=19),
             price_economy=350.0, price_extra_legroom=440.0,
             price_business=750.0, price_first=1400.0,
             available_seats=200),

        # JFK → IST  (10h,     day +3, 18:00)
        dict(flight_number="AA0100",
             departure_airport_id=jfk.id, arrival_airport_id=ist.id,
             airplane_id=b787.id,
             departure_time=base(3) + timedelta(hours=18),
             arrival_time  =base(3) + timedelta(hours=28),
             price_economy=370.0, price_extra_legroom=460.0,
             price_business=780.0, price_first=1500.0,
             available_seats=195),

        # DXB → LHR  (7h,      day +2, 08:00)
        dict(flight_number="EK0004",
             departure_airport_id=dxb.id, arrival_airport_id=lhr.id,
             airplane_id=b787.id,
             departure_time=base(2) + timedelta(hours=8),
             arrival_time  =base(2) + timedelta(hours=15),
             price_economy=420.0, price_extra_legroom=520.0,
             price_business=900.0, price_first=1800.0,
             available_seats=210),

        # LHR → DXB  (7h,      day +5, 21:00)
        dict(flight_number="EK0003",
             departure_airport_id=lhr.id, arrival_airport_id=dxb.id,
             airplane_id=b787.id,
             departure_time=base(5) + timedelta(hours=21),
             arrival_time  =base(6) + timedelta(hours=4),
             price_economy=410.0, price_extra_legroom=510.0,
             price_business=880.0, price_first=1750.0,
             available_seats=205),

        # FRA → DXB  (6h,      day +3, 10:00)
        dict(flight_number="LH0620",
             departure_airport_id=fra.id, arrival_airport_id=dxb.id,
             airplane_id=a321.id,
             departure_time=base(3) + timedelta(hours=10),
             arrival_time  =base(3) + timedelta(hours=16),
             price_economy=310.0, price_extra_legroom=390.0,
             price_business=680.0, price_first=None,
             available_seats=150),

        # DXB → FRA  (7h,      day +7, 03:00)
        dict(flight_number="EK0046",
             departure_airport_id=dxb.id, arrival_airport_id=fra.id,
             airplane_id=a321.id,
             departure_time=base(7) + timedelta(hours=3),
             arrival_time  =base(7) + timedelta(hours=10),
             price_economy=320.0, price_extra_legroom=400.0,
             price_business=700.0, price_first=None,
             available_seats=148),

        # IST → FRA  (3h 30m,  day +5, 06:00)
        dict(flight_number="TK1630",
             departure_airport_id=ist.id, arrival_airport_id=fra.id,
             airplane_id=b737.id,
             departure_time=base(5) + timedelta(hours=6),
             arrival_time  =base(5) + timedelta(hours=9, minutes=30),
             price_economy=155.0, price_extra_legroom=205.0,
             price_business=370.0, price_first=None,
             available_seats=130),

        # FRA → IST  (3h 30m,  day +10, 13:00)
        dict(flight_number="LH1330",
             departure_airport_id=fra.id, arrival_airport_id=ist.id,
             airplane_id=b737.id,
             departure_time=base(10) + timedelta(hours=13),
             arrival_time  =base(10) + timedelta(hours=16, minutes=30),
             price_economy=160.0, price_extra_legroom=210.0,
             price_business=380.0, price_first=None,
             available_seats=128),
    ]

    new_count = 0
    for spec in flight_specs:
        if not db.query(Flight).filter(
            Flight.flight_number == spec["flight_number"]
        ).first():
            db.add(Flight(**spec, status=FlightStatus.scheduled, is_active=True))
            new_count += 1

    if new_count:
        db.commit()

    total = db.query(Flight).count()
    return total, new_count, [s["flight_number"] for s in flight_specs]


# ════════════════════════════════════════════════════════════════════════════
#  Entry point
# ════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 62)
    print("  ✈️   Airline System — Database Seed Script")
    print("=" * 62)

    # 1. Create tables
    print("\n📦  Creating tables (if not exist)…")
    Base.metadata.create_all(bind=engine)
    print("    ✅  Tables ready.")

    db = SessionLocal()
    try:
        # 2. Admin user
        print("\n👤  Seeding admin user…")
        admin, created = _upsert_admin(db)
        icon = "✅  Created" if created else "⚠️   Already existed"
        print(f"    {icon}:  {admin.email}  (role: {admin.role.value})")

        # 3. Airports
        print("\n🌍  Seeding airports…")
        airports, new_airports = _upsert_airports(db)
        total_airports = db.query(Airport).count()
        print(f"    Newly inserted: {new_airports}  |  Total in DB: {total_airports}")
        for code, ap in airports.items():
            print(f"      • {code}  —  {ap.name} ({ap.city}, {ap.country})")

        # 4. Airplanes
        print("\n✈️   Seeding airplanes…")
        planes, new_planes = _upsert_airplanes(db)
        total_planes = db.query(Airplane).count()
        print(f"    Newly inserted: {new_planes}  |  Total in DB: {total_planes}")
        for reg, pl in planes.items():
            print(f"      • {reg}  —  {pl.manufacturer} {pl.model} ({pl.total_seats} seats)")

        # 5. Flights
        print("\n🛫  Seeding flights…")
        total_flights, new_flights, flight_numbers = _upsert_flights(db, airports, planes)
        print(f"    Newly inserted: {new_flights}  |  Total in DB: {total_flights}")
        for fn in flight_numbers:
            fl = db.query(Flight).filter(Flight.flight_number == fn).first()
            if fl:
                dep_code = fl.departure_airport.iata_code
                arr_code = fl.arrival_airport.iata_code
                dep_dt   = fl.departure_time.strftime("%Y-%m-%d %H:%M")
                print(
                    f"      • {fn:<8}  {dep_code} → {arr_code}"
                    f"   {dep_dt} UTC   ${fl.price_economy:.0f} economy"
                )

        # ── Final summary ─────────────────────────────────────────────────────
        print()
        print("=" * 62)
        print("  🎉  Seed complete — summary")
        print("=" * 62)
        print(f"  Admin email      : {ADMIN_EMAIL}")
        print(f"  Admin password   : {ADMIN_PASSWORD}")
        print(f"  Airports in DB   : {total_airports}")
        print(f"  Flights in DB    : {total_flights}")
        print("=" * 62)

    finally:
        db.close()


if __name__ == "__main__":
    main()
