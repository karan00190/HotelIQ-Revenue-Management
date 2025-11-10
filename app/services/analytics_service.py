from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, timedelta
from app.models.hotel import Booking, Hotel, Room
from typing import Dict, List


def calculate_revenue_metrics(
    db: Session,
    hotel_id: int = None,
    start_date: date = None,
    end_date: date = None
) -> Dict:
    """
    Calculate revenue metrics for a given period.
    
    Returns:
    - total_revenue
    - total_bookings
    - average_daily_rate (ADR)
    - occupancy_rate
    """
    query = db.query(Booking).filter(Booking.status.in_(["confirmed", "completed"]))
    
    if hotel_id:
        query = query.filter(Booking.hotel_id == hotel_id)
    
    if start_date:
        query = query.filter(Booking.check_in_date >= start_date)
    
    if end_date:
        query = query.filter(Booking.check_out_date <= end_date)
    
    bookings = query.all()
    
    if not bookings:
        return {
            "total_revenue": 0.0,
            "total_bookings": 0,
            "average_daily_rate": 0.0,
            "occupancy_rate": 0.0,
            "period_start": start_date,
            "period_end": end_date
        }
    
    # Calculate metrics
    total_revenue = sum(b.booking_price for b in bookings)
    total_bookings = len(bookings)
    
    # Calculate total room nights
    total_room_nights = sum(
        (b.check_out_date - b.check_in_date).days for b in bookings
    )
    
    # Average Daily Rate (ADR)
    adr = total_revenue / total_room_nights if total_room_nights > 0 else 0.0
    
    # Calculate occupancy rate
    if hotel_id:
        hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
        total_rooms = hotel.total_rooms if hotel else 0
    else:
        total_rooms = db.query(func.sum(Hotel.total_rooms)).scalar() or 0
    
    if start_date and end_date:
        days_in_period = (end_date - start_date).days
    else:
        days_in_period = 180  # Default to 6 months
    
    available_room_nights = total_rooms * days_in_period
    occupancy_rate = (total_room_nights / available_room_nights * 100) if available_room_nights > 0 else 0.0
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_bookings": total_bookings,
        "average_daily_rate": round(adr, 2),
        "occupancy_rate": round(occupancy_rate, 2),
        "period_start": start_date,
        "period_end": end_date
    }


def get_daily_statistics(
    db: Session,
    hotel_id: int,
    target_date: date
) -> Dict:
    """
    Get statistics for a specific date.
    """
    bookings = db.query(Booking).filter(
        and_(
            Booking.hotel_id == hotel_id,
            Booking.check_in_date <= target_date,
            Booking.check_out_date > target_date,
            Booking.status.in_(["confirmed", "completed"])
        )
    ).all()
    
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    
    rooms_occupied = len(bookings)
    total_rooms = hotel.total_rooms if hotel else 0
    occupancy_rate = (rooms_occupied / total_rooms * 100) if total_rooms > 0 else 0.0
    
    daily_revenue = sum(b.booking_price / (b.check_out_date - b.check_in_date).days for b in bookings)
    
    return {
        "date": target_date,
        "hotel_id": hotel_id,
        "rooms_occupied": rooms_occupied,
        "total_rooms": total_rooms,
        "occupancy_rate": round(occupancy_rate, 2),
        "daily_revenue": round(daily_revenue, 2)
    }