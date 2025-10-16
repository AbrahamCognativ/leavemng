from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import uuid
import re


class NextOfKinContact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    relationship: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    is_primary: bool = False
    is_emergency_contact: bool = True
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', v)
        # Check if it's a valid phone number format
        if not re.match(r'^\+?[\d]{10,20}$', cleaned):
            raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

    @validator('relationship')
    def validate_relationship(cls, v):
        allowed_relationships = [
            'Spouse', 'Parent', 'Sibling', 'Child', 'Friend', 
            'Relative', 'Colleague', 'Other'
        ]
        if v not in allowed_relationships:
            raise ValueError(f'Relationship must be one of: {", ".join(allowed_relationships)}')
        return v


class NextOfKinCreate(BaseModel):
    relationship: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    is_primary: bool = False
    is_emergency_contact: bool = True

    @validator('phone_number')
    def validate_phone_number(cls, v):
        cleaned = re.sub(r'[^\d+]', '', v)
        if not re.match(r'^\+?[\d]{10,20}$', cleaned):
            raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

    @validator('relationship')
    def validate_relationship(cls, v):
        allowed_relationships = [
            'Spouse', 'Parent', 'Sibling', 'Child', 'Friend', 
            'Relative', 'Colleague', 'Other'
        ]
        if v not in allowed_relationships:
            raise ValueError(f'Relationship must be one of: {", ".join(allowed_relationships)}')
        return v


class NextOfKinUpdate(BaseModel):
    relationship: Optional[str] = Field(None, min_length=1, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    is_primary: Optional[bool] = None
    is_emergency_contact: Optional[bool] = None

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v:
            cleaned = re.sub(r'[^\d+]', '', v)
            if not re.match(r'^\+?[\d]{10,20}$', cleaned):
                raise ValueError('Invalid phone number format')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

    @validator('relationship')
    def validate_relationship(cls, v):
        if v:
            allowed_relationships = [
                'Spouse', 'Parent', 'Sibling', 'Child', 'Friend', 
                'Relative', 'Colleague', 'Other'
            ]
            if v not in allowed_relationships:
                raise ValueError(f'Relationship must be one of: {", ".join(allowed_relationships)}')
        return v


class NextOfKinData(BaseModel):
    next_of_kin: List[NextOfKinContact] = Field(default_factory=list)

    @validator('next_of_kin')
    def validate_primary_contact(cls, v):
        primary_contacts = [contact for contact in v if contact.is_primary]
        if len(primary_contacts) > 1:
            raise ValueError('Only one primary contact is allowed')
        return v
