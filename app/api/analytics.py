from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Optional
from app.database.connection import get_db
from app.services.analytics_service import calculate_revenue_metrics, get_daily_statistics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/revenue")
def get_revenue_analytics(
    hotel_id: Optional[int] = None,
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date for analysis"),
    db: Session = Depends(get_db)
):
    """
    Get revenue analytics for a period.
    
    Returns:
    - Total revenue
    - Total bookings
    - Average Daily Rate (ADR)
    - Occupancy rate
    """
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.now().date()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    metrics = calculate_revenue_metrics(
        db=db,
        hotel_id=hotel_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return metrics


@router.get("/daily/{hotel_id}")
def get_daily_analytics(
    hotel_id: int,
    target_date: date = Query(default=None, description="Date for analysis (default: today)"),
    db: Session = Depends(get_db)
):
    """
    Get analytics for a specific date and hotel.
    """
    if not target_date:
        target_date = datetime.now().date()
    
    stats = get_daily_statistics(db=db, hotel_id=hotel_id, target_date=target_date)
    return stats


@router.get("/summary")
def get_overall_summary(db: Session = Depends(get_db)):
    """
    Get overall system summary.
    """
    from app.models.hotel import Hotel, Room, Booking
    
    total_hotels = db.query(Hotel).count()
    total_rooms = db.query(Room).count()
    total_bookings = db.query(Booking).count()
    active_bookings = db.query(Booking).filter(Booking.status == "confirmed").count()
    
    # Revenue for current month
    first_day_of_month = date.today().replace(day=1)
    metrics = calculate_revenue_metrics(
        db=db,
        start_date=first_day_of_month,
        end_date=date.today()
    )
    
    return {
        "total_hotels": total_hotels,
        "total_rooms": total_rooms,
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "current_month_revenue": metrics["total_revenue"],
        "current_month_occupancy": metrics["occupancy_rate"]
    }