from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenData(BaseModel):
    sub: str
    exp: datetime


class CategoryBase(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class LostItemCreate(BaseModel):
    item_name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    category_id: int
    date_lost: date
    location_lost: str = Field(min_length=2, max_length=200)
    contact_info: str = Field(min_length=2, max_length=200)


class FoundItemCreate(BaseModel):
    item_name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    category_id: int
    date_found: date
    location_found: str = Field(min_length=2, max_length=200)
    finder_contact: str = Field(min_length=2, max_length=200)

