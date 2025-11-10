from pydantic import BaseModel, EmailStr, Field, validator
from datetime import date, datetime
from typing import Optional, List

# ============ Hotel Schemas ============
class HotelBase(BaseModel):
    name: str
    location: str
    total_rooms: int
    star_rating: Optional[float] = None

class HotelCreate(HotelBase):
    pass

class HotelResponse(HotelBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ Room Schemas ============
class RoomBase(BaseModel):
    room_number: str
    room_type: str
    base_price: float = Field(gt=0)
    max_occupancy: int = Field(gt=0)
    is_available: bool = True

class RoomCreate(RoomBase):
    hotel_id: int

class RoomResponse(RoomBase):
    id: int
    hotel_id: int
    
    class Config:
        from_attributes = True


# ============ Booking Schemas ============
class BookingBase(BaseModel):
    check_in_date: date
    check_out_date: date
    guest_name: str
    guest_email: Optional[str] = None
    num_guests: int = Field(gt=0)
    booking_source: Optional[str] = "direct"
    
    @validator('check_out_date')
    def check_out_after_check_in(cls, v, values):
        if 'check_in_date' in values and v <= values['check_in_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v

class BookingCreate(BookingBase):
    hotel_id: int
    room_id: int
    booking_price: float = Field(gt=0)
    base_price: float = Field(gt=0)

class BookingResponse(BookingBase):
    id: int
    hotel_id: int
    room_id: int
    booking_price: float
    base_price: float
    booking_date: datetime
    status: str
    
    class Config:
        from_attributes = True


# ============ Metrics Schemas ============
class DailyMetricsResponse(BaseModel):
    id: int
    hotel_id: int
    date: date
    occupancy_rate: Optional[float]
    rooms_occupied: Optional[int]
    rooms_available: Optional[int]
    total_revenue: Optional[float]
    average_daily_rate: Optional[float]
    revenue_per_available_room: Optional[float]
    booking_count: int
    cancellation_count: int
    calculated_at: datetime
    
    class Config:
        from_attributes = True


# ============ Analytics Schemas ============
class RevenueAnalytics(BaseModel):
    """Revenue analytics response"""
    total_revenue: float
    average_daily_rate: float
    occupancy_rate: float
    total_bookings: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class ForecastResponse(BaseModel):
    """Demand forecast response"""
    date: date
    predicted_occupancy: float
    predicted_revenue: float
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None


### **Step 3: Verify File Structure**
