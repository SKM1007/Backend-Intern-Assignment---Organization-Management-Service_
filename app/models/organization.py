from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId

# Input model for POST /org/create
class OrganizationCreate(BaseModel):
    organization_name: str = Field(..., min_length=3)
    # Admin fields are typically embedded or passed separately in practice, 
    # but based on the assignment, we will keep them separate in the router function.

# DB Model for the Master Organization Collection
class OrganizationDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    organization_name: str
    collection_name: str
    admin_user_id: PyObjectId # Foreign key reference to AdminDB
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# Output model for GET /org/get
class OrganizationOut(BaseModel):
    id: str = Field(alias="_id")
    organization_name: str
    collection_name: str
    admin_user_id: str
    
    class Config:
        populate_by_name = True