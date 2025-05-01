# Leave Management System - Backend


## Setup Instructions

### 1. Install Requirements
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
- Create a `.env` file in the backend directory if needed (for DB, secrets, etc).

### 3. Database Migration
```bash
alembic upgrade head
```

### 4. Run the Application
```bash
uvicorn app.run:app --reload
```

---

## API Endpoints

### Auth
- `POST /api/v1/auth/login` — Login and get JWT token
- `POST /api/v1/auth/invite` — Invite a user (HR/Manager)

### Users
- `GET /api/v1/users/` — List users (HR/Admin)
- `POST /api/v1/users/` — Create user (HR/Admin)
- `GET /api/v1/users/{user_id}` — Get user details
- `PUT /api/v1/users/{user_id}` — Update user
- `GET /api/v1/users/{user_id}/leave` — Get a user's leave details

### Leave Types & Policies
- `GET /api/v1/leave-types/types` — List leave types (HR/Admin/Manager/IC)
- `POST /api/v1/leave-types/types` — Create leave type (HR/Admin)
- `PUT /api/v1/leave-types/types/{leave_type_id}` — Update leave type (HR/Admin)
- `GET /api/v1/leave-types/policies` — List leave policies (HR/Admin)
- `POST /api/v1/leave-types/policies` — Create leave policy (HR/Admin)
- `PUT /api/v1/leave-types/policies/{policy_id}` — Update leave policy (HR/Admin)

### Leave Requests
- `GET /api/v1/leave/` — List leave requests
- `POST /api/v1/leave/` — Apply for leave
- `GET /api/v1/leave/{request_id}` — Get leave request details
- `PUT /api/v1/leave/{request_id}` — Update leave request
- `PATCH /api/v1/leave/{request_id}/approve` — Approve a leave request

### Org Units
- `GET /api/v1/org/` — List org units (HR/Admin)
- `POST /api/v1/org/` — Create org unit (HR/Admin)
- `GET /api/v1/org/{unit_id}` — Get org unit details (HR/Admin)
- `PUT /api/v1/org/{unit_id}` — Update org unit (HR/Admin)

---

## Notes
- Make sure your database is running and accessible.
- Adjust environment variables as needed for your setup.
- For more endpoints and details, see the FastAPI auto-generated docs at `/docs` once the server is running.
