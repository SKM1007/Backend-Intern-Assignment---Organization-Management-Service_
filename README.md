# Organization Management Service

A multi-tenant backend service built with FastAPI and MongoDB for creating and managing organizations and their administrative users.

## 🚀 Setup and Run Instructions

### Prerequisites

* Python 3.10+
* MongoDB (Must be running locally, typically on `mongodb://localhost:27017`)
* `venv` (Python Virtual Environment tool)

### 1. Clone the Repository

bash
git clone [YOUR GITHUB REPO URL]
cd org-management-service

# Create and activate the virtual environment
python3 -m venv venv
source venv/bin/activate

# Install all necessary packages
# NOTE: pydantic-settings, python-jose, and passlib[bcrypt] are crucial.
pip install fastapi uvicorn motor pydantic python-dotenv pydantic-settings python-jose 'passlib[bcrypt]' email-validator

.env

# MongoDB connection
MONGO_URI=mongodb://localhost:27017
MASTER_DB_NAME=org_master_db

# JWT settings
SECRET_KEY="your-incredibly-secure-and-long-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

#command 
uvicorn main:app --reload


## 📐 2. High Level Diagram of the Project

This diagram visually explains the multi-tenant architecture, showing how the Master Database relates to the dynamically created collections.

<img width="1024" height="918" alt="image" src="https://github.com/user-attachments/assets/c1304185-0b93-4fa1-92ef-9d619cb611b3" />



## 🧠 3. Brief Notes Explaining the Design Choices

This addresses the "Additional questions" section, showing critical thinking about the architecture.

markdown
## 💡 Architectural Design and Trade-offs

### Modular and Clean Design (Python/FastAPI)

The project uses a standard layered and modular architecture:
* **main.py:** Entry point and application lifecycle management.
* **app/core:** Contains utilities (Configuration, Database Connection, Security) that are framework-agnostic.
* **app/models:** Contains Pydantic schemas for request/response validation and data modeling (including the custom `PyObjectId` for MongoDB integration).
* **app/api/v1:** Contains the RESTful routes and business logic.

This separation ensures **clean dependency flow** (models don't depend on core, core doesn't depend on API) and enhances **testability**.

### Multi-Tenancy Approach: Shared Database, Separate Collections

This design choice was made to balance **isolation** and **cost-effectiveness**:

| Feature | Design Choice | Trade-offs & Notes |
| :--- | :--- | :--- |
| **Data Isolation** | Separate MongoDB Collections (`org_acmecorp`) per organization within a single Master Database. | **Pro:** Logically separates tenant data; simplifies backup/restore for individual tenants. **Con:** High risk of the **"Noisy Neighbor"** problem where one high-traffic tenant can degrade performance for all others. |
| **Authentication** | JWT with `org_id` in the payload. | **Pro:** Stateless and scalable authentication. **Con:** Tokens must be invalidated manually (e.g., via a blacklist check in the DB) if a password changes or an admin is deactivated before the token expires. |
| **Security** | `get_current_org_id` Dependency. | **Pro:** Enforces **tenant authorization** in a single line on every protected route, ensuring an admin can only access their own organization's resources. |

### Scalability and Alternative Design

The current design is highly scalable in terms of **deployment (FastAPI is fast)** but faces limits in terms of **database resource allocation**.

**A Better Design for Massive Scale:**
For enterprise-level isolation and greater horizontal scaling, the **"Shared Database Server, Separate Databases"** model is superior. In this alternative, each organization would have its own MongoDB **database** (not just a collection) on the shared server. This provides true resource isolation and prevents the "Noisy Neighbor" issue at the database level.

