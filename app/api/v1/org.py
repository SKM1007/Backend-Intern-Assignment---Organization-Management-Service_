from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from datetime import timedelta
from typing import Optional

from app.core.db import get_master_db, get_mongo_client
from app.core.security import (
    get_password_hash, verify_password, create_access_token, get_current_org_id
)
from app.models.organization import OrganizationCreate, OrganizationDB, OrganizationOut
from app.models.user import AdminCreate, AdminDB, AdminLogin, Token
from app.core.config import settings

router = APIRouter(prefix="/org", tags=["Organization Management"])

# --- Helper for Admin Creation (Used by Org Create) ---
async def create_admin_user(email: str, password: str, org_id: ObjectId):
    """Creates the admin user and stores them in the Master DB."""
    master_db = get_master_db()
    
    # 1. Check if user already exists (globally)
    if await master_db["master_users"].find_one({"email": email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin email already registered for another organization"
        )

    # 2. Hash password and create user record
    hashed_password = get_password_hash(password)
    admin_db_model = AdminDB(
        email=email,
        hashed_password=hashed_password,
        org_id=org_id
    )
    
    # 3. Insert admin user
    result = await master_db["master_users"].insert_one(admin_db_model.model_dump(by_alias=True))
    return result.inserted_id


# --- Functional Requirement 1: Create Organization (POST /org/create) ---
@router.post("/create", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    admin_data: AdminCreate
):
    master_db = get_master_db()
    
    # 1. Validate organization name uniqueness
    if await master_db["organizations"].find_one({"organization_name": org_data.organization_name}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already exists"
        )
    
    # 2. Prepare dynamic collection name
    collection_name = f"org_{org_data.organization_name.lower().replace(' ', '_')}"
    
    # 3. Create the initial organization document in Master DB (before admin)
    org_db_model = OrganizationDB(
        organization_name=org_data.organization_name,
        collection_name=collection_name,
        admin_user_id=ObjectId() # Temporary dummy ID
    )
    org_result = await master_db["organizations"].insert_one(org_db_model.model_dump(exclude={"admin_user_id"}, by_alias=True))
    org_id = org_result.inserted_id
    
    # 4. Create the Admin User associated with the new Org ID
    admin_id = await create_admin_user(admin_data.email, admin_data.password, org_id)
    
    # 5. Update the Organization document with the correct admin_user_id
    await master_db["organizations"].update_one(
        {"_id": org_id},
        {"$set": {"admin_user_id": admin_id}}
    )

    # 6. Dynamically create the new Mongo collection for the organization
    mongo_client = get_mongo_client()
    await mongo_client[settings.MASTER_DB_NAME].create_collection(collection_name)
    
    # 7. Return success response (refetch for complete data)
    new_org = await master_db["organizations"].find_one({"_id": org_id})
    return new_org


# --- Functional Requirement 2: Get Organization by Name (GET /org/get) ---
@router.get("/get", response_model=OrganizationOut)
async def get_organization(organization_name: str):
    master_db = get_master_db()
    organization = await master_db["organizations"].find_one(
        {"organization_name": organization_name}
    )
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return organization


# --- Functional Requirement 5: Admin Login (POST /admin/login) ---
@router.post("/admin/login", response_model=Token)
async def admin_login(admin_login_data: AdminLogin):
    master_db = get_master_db()
    
    # 1. Fetch user by email
    user_doc = await master_db["master_users"].find_one(
        {"email": admin_login_data.email}
    )
    
    if not user_doc:
        # Prevent timing attacks by giving generic error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 2. Validate password
    if not verify_password(admin_login_data.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Create JWT token
    access_token = create_access_token(
        data={
            "sub": str(user_doc["_id"]), 
            "org_id": str(user_doc["org_id"])
        }
    )
    
    # 4. Return token
    return {"access_token": access_token, "token_type": "bearer"}


# --- Functional Requirement 4: Delete Organization (DELETE /org/delete) ---
@router.delete("/delete/{organization_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_name: str,
    # Authorization check: ensures user is logged in and returns their org_id
    current_org_id: str = Depends(get_current_org_id)
):
    master_db = get_master_db()
    
    # 1. Fetch the organization to be deleted
    organization = await master_db["organizations"].find_one(
        {"organization_name": organization_name}
    )
    
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
        
    # 2. Authorization: Check if the authenticated user's org_id matches the requested org_id
    if str(organization["_id"]) != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this organization"
        )

    # 3. Delete Dynamic Collection
    mongo_client = get_mongo_client()
    collection_name = organization["collection_name"]
    await mongo_client[settings.MASTER_DB_NAME].drop_collection(collection_name)

    # 4. Delete Master Records
    await master_db["organizations"].delete_one({"_id": organization["_id"]})
    await master_db["master_users"].delete_one({"org_id": organization["_id"]})
    
    return 


# --- Functional Requirement 3: Update Organization (PUT /org/update) ---
# NOTE: This endpoint is complex due to the requirement to 'sync data to the new Table/Collection'
# Below is a simplified implementation for updating the name, without data migration.
# For full compliance, a migration utility would be needed.

@router.put("/update", response_model=OrganizationOut)
async def update_organization(
    organization_name: str,
    new_org_name: Optional[str] = None,
    current_org_id: str = Depends(get_current_org_id)
):
    master_db = get_master_db()
    
    # 1. Find the current organization
    organization = await master_db["organizations"].find_one(
        {"organization_name": organization_name}
    )
    
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # 2. Authorization Check (using the Org ID from the token)
    if str(organization["_id"]) != current_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this organization")

    update_fields = {}
    
    if new_org_name and new_org_name != organization_name:
        
        # Check if the new name is already taken
        if await master_db["organizations"].find_one({"organization_name": new_org_name}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New organization name already exists"
            )
            
        old_collection_name = organization["collection_name"]
        new_collection_name = f"org_{new_org_name.lower().replace(' ', '_')}"
        
        # A. Rename the Dynamic Collection (Data Migration/Sync handled here)
        mongo_client = get_mongo_client()
        await mongo_client[settings.MASTER_DB_NAME].get_collection(old_collection_name).rename(new_collection_name)
        
        # B. Update master records
        update_fields["organization_name"] = new_org_name
        update_fields["collection_name"] = new_collection_name

    # Apply updates to Master DB
    if update_fields:
        await master_db["organizations"].update_one(
            {"_id": organization["_id"]},
            {"$set": update_fields}
        )
        # Fetch and return the updated document
        updated_org = await master_db["organizations"].find_one({"_id": organization["_id"]})
        return updated_org
    
    return organization # Return original if no changes were made