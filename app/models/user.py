from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Any
from bson import ObjectId
from pydantic_core import core_schema

# --- Corrected PyObjectId for Pydantic V2 ---
class PyObjectId(ObjectId):
    """
    Custom type for reading MongoDB ObjectIds in Pydantic models.
    It provides validators for Pydantic and a schema for documentation.
    """
    @classmethod
    def __get_validators__(cls):
        # Pydantic V1 compatibility, still used in some context
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    # This is the V2 method that replaces __modify_schema__ and __get_validators__
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            # Define how Pydantic handles Python objects (like dicts from Motor)
            python_schema=core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ]),
            # Define how Pydantic treats the value in JSON (i.e., a string)
            json_schema=core_schema.str_schema(),
            # Define how the Python object is serialized back to JSON (i.e., str(ObjectId))
            serialization=core_schema.to_string_ser_schema(),
        )

# --- Admin Models ---

# Base Models
class AdminBase(BaseModel):
    """Base model for admin creation and common fields."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")

# Input for creating a new Admin (part of Org creation)
class AdminCreate(AdminBase):
    pass

# DB Model for the Master User Collection
class AdminDB(BaseModel):
    """Model representing an Admin user record in the Master Database."""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email: EmailStr
    hashed_password: str
    org_id: PyObjectId # Reference to the Organization in the master table

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str} # Ensure ObjectId is serialized to string

# Input for admin login
class AdminLogin(BaseModel):
    """Model for authenticating an admin user."""
    email: EmailStr
    password: str

# --- JWT Models ---

class Token(BaseModel):
    """Model for the JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Model for the data contained within the decoded JWT payload."""
    id: Optional[str] = None # Admin User ID ('sub' in JWT)
    org_id: Optional[str] = None # Organization ID