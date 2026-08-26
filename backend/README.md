# IIChE Backend API

FastAPI backend for the IIChE Student Chapter website, BIT Mesra.

## Quick Start (Docker Compose)

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Start all services (PostgreSQL + Redis + FastAPI)
docker-compose up -d

# 3. Run database migrations
docker-compose exec api alembic upgrade head

# 4. API is live at http://localhost:8000
#    - Docs: http://localhost:8000/docs
#    - Health: http://localhost:8000/health
```

## Quick Start (Local without Docker)

```bash
# 1. Install Python 3.12+
# 2. Install PostgreSQL and Redis (or use Docker just for those)

# Start just DB and Redis:
docker-compose up -d db redis

# 3. Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy and configure env vars
cp .env.example .env

# 6. Run migrations
alembic upgrade head

# 7. Start the server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

All endpoints are under `/api/v1/`. Full interactive docs at `/docs`.

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/signup` | Create account |
| POST | `/api/v1/auth/login` | Login (sets session cookie) |
| POST | `/api/v1/auth/logout` | Logout (clears session) |
| GET | `/api/v1/auth/me` | Current user profile |
| GET | `/api/v1/auth/google/login` | Google OAuth redirect |
| GET | `/api/v1/auth/google/callback` | Google OAuth callback |
| POST | `/api/v1/auth/forgot-password/request` | Request OTP |
| POST | `/api/v1/auth/forgot-password/verify-otp` | Verify OTP |
| POST | `/api/v1/auth/forgot-password/reset` | Reset password |

### Events (Public)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/events` | List active events |
| GET | `/api/v1/events/{id}` | Event details |

### Registrations (Authenticated)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/events/{id}/register` | Register for event |
| DELETE | `/api/v1/events/{id}/register` | Cancel registration |
| GET | `/api/v1/events/{id}/registration-status` | Check registration |

### Users (Authenticated)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/users/me` | User profile |
| GET | `/api/v1/users/me/registrations` | My registrations |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/events` | All events |
| POST | `/api/v1/admin/events` | Create event |
| PATCH | `/api/v1/admin/events/{id}` | Update event |
| DELETE | `/api/v1/admin/events/{id}` | Delete event |
| GET | `/api/v1/admin/events/{id}/registrations` | View registrations |
| GET | `/api/v1/admin/events/{id}/registrations/export` | CSV export |

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app entry point
    api/v1/              # Route handlers (thin)
    core/                # Config, security, dependencies
    db/                  # SQLAlchemy engine/session
    models/              # ORM models
    schemas/             # Pydantic request/response models
    services/            # Business logic
    middleware/          # Rate limiting, request IDs
  alembic/               # Database migrations
  docker-compose.yml     # Local dev stack
  Dockerfile             # Production container
```
