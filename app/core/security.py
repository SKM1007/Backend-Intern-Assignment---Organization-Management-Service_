from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.models.user import TokenData  # Import the TokenData model

# --- Hashing Context ---
# Use the bcrypt scheme for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Returns the bcrypt hash of a password."""
    return pwd_context.hash(password)


# --- JWT Token Functions ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token with user and organization data."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Ensure expiration time is included
    to_encode.update({"exp": expire}) 
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

# --- Dependency Injection for Authentication ---

# Use the login URL for the token validation scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login")

async def get_current_org_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependency that decodes the JWT and returns the authenticated Organization ID.
    Raises 401 Unauthorized if token is invalid or missing org_id.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Decode the token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 2. Extract org_id and user_id (sub)
        org_id: str = payload.get("org_id")
        user_id: str = payload.get("sub")
        
        if org_id is None or user_id is None:
            raise credentials_exception
            
        # 3. Validate and return the organization ID
        token_data = TokenData(id=user_id, org_id=org_id)
        return token_data.org_id
        
    except (JWTError, ValidationError):
        # Catch JOSE errors and Pydantic validation errors
        raise credentials_exception