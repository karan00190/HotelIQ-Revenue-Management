from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.models.hotel import Hotel
from app.models.schemas import HotelCreate, HotelResponse

router = APIRouter(prefix="/hotels", tags=["Hotels"])


@router.get("/", response_model=List[HotelResponse])
def get_all_hotels(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all hotels with pagination.
    """
    hotels = db.query(Hotel).offset(skip).limit(limit).all()
    return hotels


@router.get("/{hotel_id}", response_model=HotelResponse)
def get_hotel(hotel_id: int, db: Session = Depends(get_db)):
    """
    Get a specific hotel by ID.
    """
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with ID {hotel_id} not found"
        )
    return hotel


@router.post("/", response_model=HotelResponse, status_code=status.HTTP_201_CREATED)
def create_hotel(hotel: HotelCreate, db: Session = Depends(get_db)):
    """
    Create a new hotel.
    """
    # Check if hotel already exists
    existing = db.query(Hotel).filter(Hotel.name == hotel.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hotel '{hotel.name}' already exists"
        )
    
    db_hotel = Hotel(**hotel.model_dump())
    db.add(db_hotel)
    db.commit()
    db.refresh(db_hotel)
    return db_hotel


@router.delete("/{hotel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hotel(hotel_id: int, db: Session = Depends(get_db)):
    """
    Delete a hotel by ID.
    """
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with ID {hotel_id} not found"
        )
    
    db.delete(hotel)
    db.commit()
    return None