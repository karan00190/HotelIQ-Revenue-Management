from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, timedelta
from typing import List
from app.models.hotel import Booking, Hotel, DailyMetrics


class MetricsCalculator:
    """
    Calculates and aggregates daily metrics for hotels.
    """
    
    @staticmethod
    def calculate_daily_metrics(db: Session, hotel_id: int, target_date: date) -> DailyMetrics:
        """
        Calculate metrics for a specific hotel and date.
        """
        # Get hotel info
        hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
        if not hotel:
            raise ValueError(f"Hotel {hotel_id} not found")
        
        # Get bookings for this date
        bookings = db.query(Booking).filter(
            and_(
                Booking.hotel_id == hotel_id,
                Booking.check_in_date <= target_date,
                Booking.check_out_date > target_date,
                Booking.status.in_(["confirmed", "completed"])
            )
        ).all()
        
        # Calculate metrics
        rooms_occupied = len(bookings)
        rooms_available = hotel.total_rooms
        occupancy_rate = (rooms_occupied / rooms_available * 100) if rooms_available > 0 else 0.0
        
        # Revenue for the day (prorated)
        total_revenue = sum(
            b.booking_price / (b.check_out_date - b.check_in_date).days 
            for b in bookings
        )
        
        # ADR (Average Daily Rate)
        adr = total_revenue / rooms_occupied if rooms_occupied > 0 else 0.0
        
        # RevPAR (Revenue Per Available Room)
        revpar = total_revenue / rooms_available if rooms_available > 0 else 0.0
        
        # Booking counts for the day
        booking_count = db.query(Booking).filter(
            and_(
                Booking.hotel_id == hotel_id,
                Booking.check_in_date == target_date
            )
        ).count()
        
        cancellation_count = db.query(Booking).filter(
            and_(
                Booking.hotel_id == hotel_id,
                Booking.check_in_date == target_date,
                Booking.status == "cancelled"
            )
        ).count()
        
        # Create or update metric
        metric = db.query(DailyMetrics).filter(
            and_(
                DailyMetrics.hotel_id == hotel_id,
                DailyMetrics.date == target_date
            )
        ).first()
        
        if metric:
            # Update existing
            metric.occupancy_rate = round(occupancy_rate, 2)
            metric.rooms_occupied = rooms_occupied
            metric.rooms_available = rooms_available
            metric.total_revenue = round(total_revenue, 2)
            metric.average_daily_rate = round(adr, 2)
            metric.revenue_per_available_room = round(revpar, 2)
            metric.booking_count = booking_count
            metric.cancellation_count = cancellation_count
            metric.calculated_at = func.now()
        else:
            # Create new
            metric = DailyMetrics(
                hotel_id=hotel_id,
                date=target_date,
                occupancy_rate=round(occupancy_rate, 2),
                rooms_occupied=rooms_occupied,
                rooms_available=rooms_available,
                total_revenue=round(total_revenue, 2),
                average_daily_rate=round(adr, 2),
                revenue_per_available_room=round(revpar, 2),
                booking_count=booking_count,
                cancellation_count=cancellation_count
            )
            db.add(metric)
        
        db.commit()
        db.refresh(metric)
        
        return metric
    
    @staticmethod
    def calculate_date_range_metrics(
        db: Session,
        hotel_id: int,
        start_date: date,
        end_date: date
    ) -> List[DailyMetrics]:
        """
        Calculate metrics for a date range.
        """
        metrics = []
        current_date = start_date
        
        while current_date <= end_date:
            metric = MetricsCalculator.calculate_daily_metrics(db, hotel_id, current_date)
            metrics.append(metric)
            current_date += timedelta(days=1)
        
        return metrics
    
    @staticmethod
    def recalculate_all_metrics(db: Session) -> dict:
        """
        Recalculate all daily metrics for all hotels.
        """
        print("🔄 Recalculating all daily metrics...")
        
        # Get all hotels
        hotels = db.query(Hotel).all()
        
        # Get date range from bookings
        earliest = db.query(func.min(Booking.check_in_date)).scalar()
        latest = db.query(func.max(Booking.check_out_date)).scalar()
        
        if not earliest or not latest:
            return {"message": "No bookings found"}
        
        total_calculated = 0
        
        for hotel in hotels:
            metrics = MetricsCalculator.calculate_date_range_metrics(
                db, hotel.id, earliest, latest
            )
            total_calculated += len(metrics)
            print(f"  ✅ Calculated {len(metrics)} days for {hotel.name}")
        
        print(f"✅ Total metrics calculated: {total_calculated}")
        
        return {
            "hotels_processed": len(hotels),
            "metrics_calculated": total_calculated,
            "date_range": {
                "start": earliest.isoformat(),
                "end": latest.isoformat()
            }
        }