from app.database.connection import engine, Base
from app.models.hotel import Hotel, Room, Booking, DailyMetrics

def init_database():
    """
    Create all database tables.
    Run this once to set up the database.
    """
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    init_database()