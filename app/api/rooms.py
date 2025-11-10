from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.models.hotel import Room
from app.models.schemas import RoomCreate, RoomResponse

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("/", response_model=List[RoomResponse])
def get_all_rooms(
    hotel_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all rooms, optionally filtered by hotel.
    """
    query = db.query(Room)
    
    if hotel_id:
        query = query.filter(Room.hotel_id == hotel_id)
    
    rooms = query.offset(skip).limit(limit).all()
    return rooms


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: int, db: Session = Depends(get_db)):
    """
    Get a specific room by ID.
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found"
        )
    return room


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    """
    Create a new room.
    """
    db_room = Room(**room.model_dump())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room