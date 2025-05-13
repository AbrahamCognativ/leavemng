# ---- Base image ----
FROM python:3.12-slim AS base

# ---- Set environment variables ----
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# ---- Set work directory ----
WORKDIR /app

# ---- Install system dependencies ----
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# ---- Install Python dependencies ----
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ---- Copy project files ----
COPY . .

# ---- Alembic migration entrypoint ----
# (Assumes alembic.ini and migrations/ are present)
RUN alembic upgrade head

# ---- Expose port ----
EXPOSE 8000

# ---- Run the application ----
CMD ["uvicorn", "app.run:app", "--host", "0.0.0.0", "--port", "8000"]
