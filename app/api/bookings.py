from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database.connection import get_db
from app.models.hotel import Booking
from app.models.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get("/", response_model=List[BookingResponse])
def get_all_bookings(
    hotel_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all bookings with optional filters.
    
    - **hotel_id**: Filter by hotel
    - **status**: Filter by status (confirmed, cancelled, completed)
    - **start_date**: Filter bookings from this date
    - **end_date**: Filter bookings until this date
    """
    query = db.query(Booking)
    
    if hotel_id:
        query = query.filter(Booking.hotel_id == hotel_id)
    
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    
    if start_date:
        query = query.filter(Booking.check_in_date >= start_date)
    
    if end_date:
        query = query.filter(Booking.check_out_date <= end_date)
    
    bookings = query.order_by(Booking.check_in_date.desc()).offset(skip).limit(limit).all()
    return bookings


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """
    Get a specific booking by ID.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    return booking


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    """
    Create a new booking.
    """
    db_booking = Booking(**booking.model_dump())
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.patch("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    """
    Cancel a booking.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking