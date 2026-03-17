"""
DATABASE MANAGEMENT GUIDE
═════════════════════════════════════════════════════════════

This guide explains how to use the manage_db.py script to manage your airline database.

INSTALLATION & SETUP
────────────────────

1. Navigate to backend directory:
   cd airline_system/backend

2. Ensure your virtual environment is activated and dependencies installed:
   pip install -r requirements.txt

USAGE EXAMPLES
──────────────

1. UPGRADE USER TO ADMIN
   Change any user's role from 'passenger' to 'admin':
   
   python manage_db.py --upgrade-user meka@gmail.com
   
   Output:
   ✅ User 'meka@gmail.com' role upgraded: passenger → admin
      ID: 1
      Name: User Name
      Status: Active


2. CREATE TEST FLIGHT (BISHKEK → ISTANBUL)
   Create a sample flight for booking tests:
   
   python manage_db.py --create-flight
   
   Output:
   ✅ Flight created successfully!
      Flight number: AK777
      Route: Bishkek (FRU) → Istanbul (IST)
      Departure: 2026-03-01 10:00
      Arrival: 2026-03-01 15:00
      Aircraft: Boeing 737-800 (UP-B3701)
      Pricing:
        - Standard: $180.0
        - Extra Legroom: $230.0
        - Business: $420.0
        - First: $800.0
      Available seats: 120


3. UPGRADE USER AND CREATE FLIGHT (COMBINED)
   Do both operations at once:
   
   python manage_db.py --upgrade-user meka@gmail.com --create-flight
   
   This will:
   - Make meka@gmail.com an admin user
   - Create the Bishkek → Istanbul test flight


4. CREATE TEST PASSENGER USER
   Create a new passenger account for testing:
   
   python manage_db.py --create-test-user testuser@example.com
   
   Output:
   ✅ Test user created!
      Email: testuser@example.com
      Password: test1234
      Name: Test User


5. LIST ALL USERS
   Display all users in the database:
   
   python manage_db.py --list-users
   
   Output:
   📋 Users in database:
   ──────────────────────
   ID: 1
     Email: meka@gmail.com
     Name: User Name
     Role: admin
     Active: Yes
   
   ID: 2
     Email: testuser@example.com
     Name: Test User
     Role: passenger
     Active: Yes


6. LIST ALL FLIGHTS
   Display all flights in the database:
   
   python manage_db.py --list-flights
   
   Output:
   ✈️  Flights in database:
   ────────────────────────────
   Flight: AK777
     Route: Bishkek → Istanbul
     IATA: FRU → IST
     Departure: 2026-03-01 10:00
     Arrival: 2026-03-01 15:00
     Status: SCHEDULED
     Price (Economy): $180.0
     Available Seats: 120


7. GET HELP
   Show all available commands:
   
   python manage_db.py --help
   python manage_db.py -h


COMBINED COMMANDS
─────────────────

You can combine multiple flags:

# Upgrade user AND create flight AND list both
python manage_db.py --upgrade-user meka@gmail.com --create-flight --list-users --list-flights

# Create new user AND list all users
python manage_db.py --create-test-user newuser@test.com --list-users


COMMON WORKFLOWS
────────────────

Workflow 1: First-Time Setup for Testing
────────────────────────────────────────
1. Create a test passenger:
   python manage_db.py --create-test-user passenger@test.com

2. Create admin user:
   python manage_db.py --upgrade-user meka@gmail.com

3. Create sample flight:
   python manage_db.py --create-flight

4. Verify everything:
   python manage_db.py --list-users --list-flights


Workflow 2: Quick Booking Test
──────────────────────────────
1. Ensure you have a flight:
   python manage_db.py --list-flights
   
   (If no flights, run: python manage_db.py --create-flight)

2. Start your Flutter app and search for flights:
   - From: Bishkek (FRU)
   - To: Istanbul (IST)
   - Date: Today

3. Select flight AK777 and book!


ERROR HANDLING
──────────────

Error: "User with email 'xxx@xxx.com' not found"
→ User doesn't exist. Create them first or check the email address.

Error: "Istanbul airport (IST) not found in database"
→ Run database seed: Check that seed.py has been executed on startup.

Error: "No airplanes found in database"
→ Run database seed or manually create an airplane via API.

Error: "Flight 'AK777' already exists"
→ Flight is already in database. This is normal and safe.


DATABASE LOCATION
─────────────────
SQLite database file: airline_system/backend/airline.db

To reset database completely:
1. Delete: airline_system/backend/airline.db
2. Run your FastAPI app (it will auto-create and seed database)
3. Use manage_db.py to create custom data


TESTING WITH MOBILE APP
───────────────────────

After running the script:

1. Get admin credentials:
   Email: meka@gmail.com
   Password: (you need to know original password)
   
   OR create with known password:
   python manage_db.py --create-test-user admin-test@test.com

2. Log in to Flutter app with test account

3. Search for flights (Bishkek → Istanbul)

4. Book the AK777 flight with Standard/Business/First class


API ENDPOINTS YOU CAN TEST
──────────────────────────

After running the script, test these endpoints:

1. Login (get token):
   POST /auth/login
   {
     "email": "meka@gmail.com",
     "password": "<password>"
   }

2. Search flights:
   GET /flights/search?from_iata=FRU&to_iata=IST&departure_date=2026-03-01

3. View airports:
   GET /flights/airports

4. Create booking:
   POST /bookings/
   {
     "flight_id": 1,
     "category": "standard",
     "seat_number": null
   }


SCRIPT FEATURES
───────────────

✅ SQLAlchemy ORM integration with proper sessions
✅ Error handling and rollback on failure
✅ Safe user role upgrades (checks existing role)
✅ Auto-create missing airports
✅ Flight duplication prevention
✅ Detailed console output with emojis
✅ Command-line argument parsing
✅ Can be run multiple times safely
✅ Transaction-based operations


NOTES
─────

• The script uses transactions (db.commit/rollback)
• Multiple runs are safe - duplicates are detected
• Created with SQLAlchemy ORM best practices
• Works with SQLite database (airline.db)
• All passwords hashed using bcrypt
• Timestamps auto-generated by database
"""
