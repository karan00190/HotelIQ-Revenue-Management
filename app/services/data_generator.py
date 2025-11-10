import random
from datetime import datetime, timedelta, date
from typing import List
from sqlalchemy.orm import Session
from app.models.hotel import Hotel, Room, Booking

# Hotel data
HOTELS = [
    {
        "name": "Grand Plaza Mumbai",
        "location": "Mumbai, Maharashtra",
        "total_rooms": 150,
        "star_rating": 5.0
    },
    {
        "name": "Coastal Inn Goa",
        "location": "Goa",
        "total_rooms": 80,
        "star_rating": 4.0
    },
    {
        "name": "Heritage Stay Jaipur",
        "location": "Jaipur, Rajasthan",
        "total_rooms": 60,
        "star_rating": 4.5
    }
]

ROOM_TYPES = ["Standard", "Deluxe", "Suite", "Executive"]
BOOKING_SOURCES = ["website", "booking.com", "direct", "expedia", "makemytrip"]
GUEST_NAMES = [
    "Rahul Sharma", "Priya Patel", "Amit Kumar", "Sneha Reddy", "Vikram Singh",
    "Anjali Gupta", "Rohan Desai", "Pooja Mehta", "Arjun Nair", "Kavya Iyer",
    "Sanjay Verma", "Neha Kapoor", "Karan Shah", "Riya Malhotra", "Aditya Joshi"
]


def generate_hotels(db: Session) -> List[Hotel]:
    """
    Generate and insert hotel records.
    Returns list of created hotels.
    """
    hotels = []
    for hotel_data in HOTELS:
        # Check if hotel already exists
        existing = db.query(Hotel).filter(Hotel.name == hotel_data["name"]).first()
        if existing:
            hotels.append(existing)
            continue
            
        hotel = Hotel(**hotel_data)
        db.add(hotel)
        hotels.append(hotel)
    
    db.commit()
    print(f"✅ Generated {len(hotels)} hotels")
    return hotels


def generate_rooms(db: Session, hotels: List[Hotel]) -> List[Room]:
    """
    Generate rooms for each hotel.
    Returns list of created rooms.
    """
    rooms = []
    
    for hotel in hotels:
        # Check if rooms already exist for this hotel
        existing_count = db.query(Room).filter(Room.hotel_id == hotel.id).count()
        if existing_count > 0:
            existing_rooms = db.query(Room).filter(Room.hotel_id == hotel.id).all()
            rooms.extend(existing_rooms)
            continue
        
        # Generate rooms based on hotel capacity
        rooms_to_create = hotel.total_rooms
        
        for i in range(1, rooms_to_create + 1):
            # Distribute room types
            if i <= rooms_to_create * 0.4:
                room_type = "Standard"
                base_price = random.uniform(3000, 5000)
            elif i <= rooms_to_create * 0.7:
                room_type = "Deluxe"
                base_price = random.uniform(5000, 8000)
            elif i <= rooms_to_create * 0.9:
                room_type = "Executive"
                base_price = random.uniform(8000, 12000)
            else:
                room_type = "Suite"
                base_price = random.uniform(12000, 20000)
            
            # Adjust price by hotel rating
            base_price *= (hotel.star_rating / 4.0)
            
            room = Room(
                hotel_id=hotel.id,
                room_number=f"{(i // 10) + 1}{i % 10 if i % 10 != 0 else 0:02d}",
                room_type=room_type,
                base_price=round(base_price, 2),
                max_occupancy=2 if room_type in ["Standard", "Deluxe"] else 4,
                is_available=True
            )
            db.add(room)
            rooms.append(room)
    
    db.commit()
    print(f"✅ Generated {len(rooms)} rooms")
    return rooms


def generate_bookings(db: Session, rooms: List[Room], num_bookings: int = 500) -> List[Booking]:
    """
    Generate historical booking data for analytics.
    Creates bookings for the past 6 months.
    """
    bookings = []
    
    # Check if bookings already exist
    existing_count = db.query(Booking).count()
    if existing_count >= num_bookings:
        print(f"ℹ️  {existing_count} bookings already exist")
        return db.query(Booking).all()
    
    # Generate bookings for past 6 months
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    for _ in range(num_bookings):
        room = random.choice(rooms)
        
        # Random check-in date in past 6 months
        days_offset = random.randint(0, 180)
        check_in = start_date + timedelta(days=days_offset)
        
        # Random stay duration (1-7 nights)
        stay_duration = random.randint(1, 7)
        check_out = check_in + timedelta(days=stay_duration)
        
        # Don't create future bookings
        if check_in > end_date:
            continue
        
        # Calculate price with dynamic pricing factors
        base_price = room.base_price
        
        # Weekend premium (Friday, Saturday)
        if check_in.weekday() in [4, 5]:
            price_multiplier = random.uniform(1.2, 1.5)
        else:
            price_multiplier = random.uniform(0.85, 1.15)
        
        # Seasonal factor (higher in Dec, lower in monsoon)
        month = check_in.month
        if month in [12, 1, 10, 11]:  # Peak season
            price_multiplier *= random.uniform(1.1, 1.3)
        elif month in [6, 7, 8]:  # Monsoon (off-season)
            price_multiplier *= random.uniform(0.7, 0.9)
        
        booking_price = round(base_price * price_multiplier * stay_duration, 2)
        
        # Random status (90% confirmed, 10% cancelled)
        status = "confirmed" if random.random() < 0.9 else "cancelled"
        if check_out < end_date:
            status = "completed"
        
        booking = Booking(
            hotel_id=room.hotel_id,
            room_id=room.id,
            check_in_date=check_in,
            check_out_date=check_out,
            guest_name=random.choice(GUEST_NAMES),
            guest_email=f"{random.choice(GUEST_NAMES).lower().replace(' ', '.')}@example.com",
            num_guests=random.randint(1, room.max_occupancy),
            booking_price=booking_price,
            base_price=base_price * stay_duration,
            booking_date=datetime.now() - timedelta(days=days_offset + random.randint(1, 30)),
            booking_source=random.choice(BOOKING_SOURCES),
            status=status
        )
        
        db.add(booking)
        bookings.append(booking)
    
    db.commit()
    print(f"✅ Generated {len(bookings)} bookings")
    return bookings


def generate_all_data(db: Session):
    """
    Generate complete dataset: hotels, rooms, and bookings.
    """
    print("\n🏗️  Generating synthetic data...")
    print("=" * 50)
    
    # Generate hotels
    hotels = generate_hotels(db)
    
    # Generate rooms
    rooms = generate_rooms(db, hotels)
    
    # Generate bookings
    bookings = generate_bookings(db, rooms, num_bookings=500)
    
    print("=" * 50)
    print(f"✅ Data generation complete!")
    print(f"   - Hotels: {len(hotels)}")
    print(f"   - Rooms: {len(rooms)}")
    print(f"   - Bookings: {len(bookings)}")
    print("=" * 50)
    
    return {
        "hotels": len(hotels),
        "rooms": len(rooms),
        "bookings": len(bookings)
    }