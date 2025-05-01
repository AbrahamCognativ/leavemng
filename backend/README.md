# Leave Management System - Backend

## Setup

1. Python 3.10+
2. FastAPI
3. SQLAlchemy
4. Alembic
5. Pydantic
6. Uvicorn
7. python-jose
8. passlib
9. psycopg2-binary
10. python-multipart
11. boto3 (for S3)
12. email-validator

## Structure
- app/
  - api/v1/routers/
  - core/
  - models/
  - schemas/
  - crud/
  - db/
  - main.py
- alembic/
- requirements.txt
- Dockerfile

## To initialize:
- Install requirements
- Run Alembic migrations
- Start FastAPI with Uvicorn
