"""
manage_db.py — Database management script
──────────────────────────────────────────────────────
Usage:
  python manage_db.py --upgrade-user meka@gmail.com
  python manage_db.py --create-flight
  python manage_db.py --upgrade-user meka@gmail.com --create-flight
"""

import sys
import argparse
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Adjust path to import app modules
sys.path.insert(0, 'app')

from app.database import SessionLocal, Base, engine
from app.models import (
    User, UserRole, Airport, Airplane, Flight, FlightStatus
)
from app.auth import hash_password


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


def upgrade_user_to_admin(email: str) -> bool:
    """Change user role from passenger to admin."""
    db = get_db()
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found in database")
            return False
        
        if user.role == UserRole.admin:
            print(f"⚠️  User '{email}' is already an admin")
            return True
        
        # Change role to admin
        old_role = user.role
        user.role = UserRole.admin
        db.commit()
        
        print(f"✅ User '{email}' role upgraded: {old_role} → {user.role}")
        print(f"   ID: {user.id}")
        print(f"   Name: {user.full_name}")
        print(f"   Status: {'Active' if user.is_active else 'Inactive'}")
        return True
        
    except Exception as e:
        print(f"❌ Error upgrading user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def create_bishkek_istanbul_flight() -> bool:
    """Create a test flight: Bishkek (FRU) → Istanbul (IST)."""
    db = get_db()
    try:
        # Check if Bishkek airport exists, if not create it
        bishkek = db.query(Airport).filter(Airport.iata_code == "FRU").first()
        if not bishkek:
            bishkek = Airport(
                iata_code="FRU",
                icao_code="UAFM",
                name="Manas International Airport",
                city="Bishkek",
                country="Kyrgyzstan",
                timezone="Asia/Bishkek"
            )
            db.add(bishkek)
            db.flush()
            print("📍 Created new airport: Bishkek (FRU)")
        else:
            print(f"📍 Found airport: {bishkek.city} ({bishkek.iata_code})")

        # Get Istanbul airport
        istanbul = db.query(Airport).filter(Airport.iata_code == "IST").first()
        if not istanbul:
            print("❌ Istanbul airport (IST) not found in database")
            return False
        print(f"📍 Found airport: {istanbul.city} ({istanbul.iata_code})")

        # Get an airplane
        airplane = db.query(Airplane).first()
        if not airplane:
            print("❌ No airplanes found in database")
            return False
        print(f"✈️  Using airplane: {airplane.model} ({airplane.registration})")

        # Check if flight already exists
        flight_number = "AK777"
        existing_flight = db.query(Flight).filter(
            Flight.flight_number == flight_number
        ).first()
        
        if existing_flight:
            print(f"⚠️  Flight '{flight_number}' already exists")
            print(f"   Departure: {existing_flight.departure_time}")
            print(f"   Price: ${existing_flight.price_economy}")
            return True

        # Create the flight
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        flight = Flight(
            flight_number=flight_number,
            departure_airport_id=bishkek.id,
            arrival_airport_id=istanbul.id,
            airplane_id=airplane.id,
            departure_time=base_date + timedelta(hours=10),  # 10:00 AM
            arrival_time=base_date + timedelta(hours=15),    # 15:00 PM (5 hour flight)
            status=FlightStatus.scheduled,
            price_economy=180.0,
            price_extra_legroom=230.0,
            price_business=420.0,
            price_first=800.0,
            available_seats=120,
            is_active=True,
        )
        
        db.add(flight)
        db.commit()
        
        print(f"\n✅ Flight created successfully!")
        print(f"   Flight number: {flight.flight_number}")
        print(f"   Route: {bishkek.city} (FRU) → {istanbul.city} (IST)")
        print(f"   Departure: {flight.departure_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Arrival: {flight.arrival_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Aircraft: {airplane.model} ({airplane.registration})")
        print(f"   Pricing:")
        print(f"     - Standard: ${flight.price_economy}")
        print(f"     - Extra Legroom: ${flight.price_extra_legroom}")
        print(f"     - Business: ${flight.price_business}")
        print(f"     - First: ${flight.price_first}")
        print(f"   Available seats: {flight.available_seats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating flight: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def create_test_user(email: str, name: str, password: str = "test1234") -> bool:
    """Create a test user if doesn't exist."""
    db = get_db()
    try:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"⚠️  User '{email}' already exists")
            return True
        
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=name,
            role=UserRole.passenger,
            is_active=True,
        )
        db.add(user)
        db.commit()
        
        print(f"✅ Test user created!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Name: {name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def list_users() -> None:
    """List all users in database."""
    db = get_db()
    try:
        users = db.query(User).all()
        
        if not users:
            print("No users found in database")
            return
        
        print("\n📋 Users in database:")
        print("-" * 70)
        for user in users:
            print(f"ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Name: {user.full_name}")
            print(f"  Role: {user.role.value}")
            print(f"  Active: {'Yes' if user.is_active else 'No'}")
            print()
    finally:
        db.close()


def list_flights() -> None:
    """List all flights in database."""
    db = get_db()
    try:
        flights = db.query(Flight).all()
        
        if not flights:
            print("No flights found in database")
            return
        
        print("\n✈️  Flights in database:")
        print("-" * 80)
        for flight in flights:
            print(f"Flight: {flight.flight_number}")
            print(f"  Route: {flight.departure_airport.city} → {flight.arrival_airport.city}")
            print(f"  IATA: {flight.departure_airport.iata_code} → {flight.arrival_airport.iata_code}")
            print(f"  Departure: {flight.departure_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Arrival: {flight.arrival_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Status: {flight.status.value}")
            print(f"  Price (Economy): ${flight.price_economy}")
            print(f"  Available Seats: {flight.available_seats}")
            print()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Airline Database Management Script"
    )
    
    parser.add_argument(
        "--upgrade-user",
        type=str,
        metavar="EMAIL",
        help="Upgrade user role to admin (e.g., --upgrade-user meka@gmail.com)"
    )
    
    parser.add_argument(
        "--create-flight",
        action="store_true",
        help="Create test flight Bishkek → Istanbul"
    )
    
    parser.add_argument(
        "--create-test-user",
        type=str,
        metavar="EMAIL",
        help="Create a test passenger user"
    )
    
    parser.add_argument(
        "--list-users",
        action="store_true",
        help="List all users in database"
    )
    
    parser.add_argument(
        "--list-flights",
        action="store_true",
        help="List all flights in database"
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    print("=" * 80)
    print("🛫 Airline Database Management")
    print("=" * 80)
    print()
    
    # Execute requested operations
    if args.upgrade_user:
        upgrade_user_to_admin(args.upgrade_user)
        print()
    
    if args.create_flight:
        create_bishkek_istanbul_flight()
        print()
    
    if args.create_test_user:
        create_test_user(args.create_test_user, "Test User")
        print()
    
    if args.list_users:
        list_users()
        print()
    
    if args.list_flights:
        list_flights()
        print()
    
    print("=" * 80)
    print("✅ Done!")
    print("=" * 80)


if __name__ == "__main__":
    main()
