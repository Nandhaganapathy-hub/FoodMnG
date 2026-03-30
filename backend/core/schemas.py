from datetime import date, time
from typing import Optional, List
from ninja import Schema

class SignUpSchema(Schema):
    username: str
    email: str
    password: str
    role: str  # canteen_admin or ngo
    # Canteen fields
    canteen_name: Optional[str] = None
    canteen_location: Optional[str] = None
    # NGO fields
    ngo_name: Optional[str] = None
    ngo_address: Optional[str] = None
    ngo_contact_person: Optional[str] = None
    ngo_phone: Optional[str] = None

class RecordIn(Schema):
    date: date
    day: str
    meal_menu_info: Optional[str] = ""
    cooked: int
    surplus: int
    no_members: int

class RecordOut(Schema):
    id: int
    date: date
    day: str
    meal_menu_info: str
    cooked: int
    surplus: int
    no_members: int
    canteen_name: str

class PredictionOut(Schema):
    predicted_footfall: int
    predicted_surplus: int
    confidence: float
    date: date

class AlterRequestSchema(Schema):
    alter_id: int
    requested_quantity: Optional[int] = None
    notes: Optional[str] = None

class UserProfileOut(Schema):
    id: int
    username: str
    email: str
    role: str
    canteen: Optional[dict] = None
    ngo: Optional[dict] = None