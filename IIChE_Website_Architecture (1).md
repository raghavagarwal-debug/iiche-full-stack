# IIChE Website — Full System Architecture & Implementation Spec

This document is a complete technical specification for the IIChE website. It covers authentication (email/password, forgot password via OTP, Google Sign-In), database design, API structure, security, observability, and infrastructure decisions (Docker, Redis, CDN, Kubernetes) for an expected load of around 500 registered users with a target peak of ~500 HTTP requests/second after load testing and tuning.

Use this as a build spec for an AI coding assistant (e.g. Antigravity).

**Important constraint:** The existing IIChE frontend is already designed and must remain visually unchanged. This is a backend + integration task, not a redesign. Do not rebuild working UI — connect it to a real backend.

---

## 1. Project Objective

The system must support:

- Email and password account creation
- Email and password login
- Logout, and login again later
- Forgot password using an email OTP
- OTP verification through a dedicated page
- Password reset using a new password + confirm password
- Google Sign-In
- Persistent user data in PostgreSQL
- Event registration **infrastructure** for authenticated users — fully built now, but **kept switched off** on the live site until IIChE actually has an event open for registration (see Section 22)
- IIChE admin access to event registration data
- A backend built on FastAPI
- An architecture suitable for ~500 registered users, capable of a target peak of ~500 requests/second after proper load testing and tuning
- Docker-based deployment
- CI/CD
- CDN and edge protection where useful
- A clear path to Kubernetes later, without introducing that complexity at the start

**Do not redesign the frontend. Integrate the backend with the existing UI.**

---

## 2. Recommended Architecture

Use a **modular monolith**. Do not split into microservices at this stage.

**Frontend**
- Existing React/Vite frontend
- Preserve current UI, routes, styling, animations, and design tokens wherever possible

**Backend**
- Python + FastAPI
- Uvicorn (ASGI server)
- SQLAlchemy 2.x
- Alembic for database migrations
- Pydantic for settings and request/response validation

**Database**
- PostgreSQL (managed service in production)
- Connection pooling
- Indexes and constraints for uniqueness/performance-critical queries

**Authentication**
- Email/password with Argon2id hashing
- Secure server-side authentication cookies (HttpOnly, Secure, SameSite) as the primary session mechanism
- Google OAuth 2.0 / OpenID Connect
- Never store Google passwords
- Support linking a Google login to an existing email/password account when the verified email matches

**Supporting infrastructure**
- **Redis** — rate limiting, OTP attempt counters/cooldowns, short-lived OAuth state, other ephemeral data. Redis is never the source of truth for permanent data.
- A real transactional email provider (not a personal Gmail SMTP account) for OTP delivery
- Cloudflare or equivalent CDN / WAF / DNS
- Docker for reproducible environments
- GitHub Actions (or equivalent) for CI/CD
- Centralized logging and monitoring

---

## 3. High-Level Request Flow

```
Browser
  ↓
CDN / DNS / WAF   (Cloudflare)
  ↓
Load Balancer / Reverse Proxy
  ↓
FastAPI application (one or more replicas)
  ├──→ Redis           (rate limits, OTP state, OAuth state)
  ├──→ PostgreSQL       (users, events, registrations — source of truth)
  ├──→ Email provider   (OTP delivery)
  └──→ Google           (OAuth flow)
```

The frontend **never** connects directly to PostgreSQL or Redis. The browser only talks to FastAPI, which enforces authentication, authorization, and all business rules before touching the database.

---

## 4. Authentication Requirements

### 4.1 Create Account

Existing "Create Account" UI fields: full name, email, password, confirm password.

Flow:
1. User submits the form.
2. Frontend performs basic validation (format, password match).
3. Frontend sends data to FastAPI over HTTPS.
4. Backend re-validates everything server-side — never trust client-side validation alone.
5. Backend normalizes the email (lowercase/trim).
6. Backend checks whether the email already exists.
7. Backend hashes the password with **Argon2id**.
8. Backend creates the user record.
9. Backend returns a success response.
10. User can now log in.

Optional production enhancement: require email verification before the account is fully active.

**Never store plaintext passwords.**

### 4.2 Email + Password Login

Existing login page: email, password, Login button, Forgot Password, Create Account, Sign in with Google.

Flow:
1. User submits email + password.
2. Backend normalizes email, retrieves the user, verifies the password hash.
3. Backend checks the account is active.
4. Backend creates a secure authenticated session and issues a **secure HTTP-only cookie**.
5. Frontend treats the user as authenticated based on a subsequent `GET /api/v1/auth/me` call — never based on client-stored state alone.

**Session cookie requirements:**
- `HttpOnly`
- `Secure`
- `SameSite` configured appropriately for the deployment (e.g. `Lax` or `None` depending on whether frontend/backend share a domain)
- Reasonable expiration
- A rotation/invalidation strategy

Do not store long-lived authentication tokens in `localStorage` unless there's a strong architectural reason to.

Provide:
```
GET /api/v1/auth/me
```
Returns the currently authenticated user's safe profile info (never the password hash).

### 4.3 Logout

```
POST /api/v1/auth/logout
```
Must invalidate the active session. After logout, protected endpoints reject the old session, and the frontend returns to the public/unauthenticated state. The user must be able to log in again afterward.

### 4.4 Forgot Password (OTP via Email) Flow

Full intended flow:

```
Login page → Forgot Password → Enter email → OTP sent to email
  → OTP verification page → Enter OTP
  → Create New Password page → Enter + confirm new password
  → Password reset successful → Login again with new password
```

**Step 1 — Request reset**
```
POST /api/v1/auth/forgot-password/request
Body: { "email": "user@example.com" }
```
Backend behavior:
1. Normalize the email.
2. Generate a cryptographically secure 6-digit OTP.
3. Store only a **hashed** representation of the OTP (never plaintext) in the database or Redis.
4. Associate it with the user/reset request.
5. Set a short expiry (~10 minutes).
6. Apply a resend cooldown (e.g. 60 seconds).
7. Apply per-email and per-IP rate limiting (via Redis).
8. Send the OTP by email through the transactional email provider.
9. Return a **generic** response that never reveals whether the account exists:
```json
{ "message": "If an account exists for this email, an OTP has been sent." }
```

**Step 2 — Verify OTP**
```
POST /api/v1/auth/forgot-password/verify-otp
Body: { "email": "user@example.com", "otp": "123456" }
```
Backend checks: OTP exists, not expired, not already used, matches, attempt limit not exceeded, reset request still valid. On success, issue a **short-lived password reset token** — the OTP itself must never double as a permanent credential.

**Step 3 — Reset password**
```
POST /api/v1/auth/forgot-password/reset
Body: { "reset_token": "...", "new_password": "...", "confirm_password": "..." }
```
Backend must: validate the reset token, validate password strength, hash the new password (Argon2id), replace the old hash, invalidate the reset token, invalidate older active sessions if appropriate, and return success. Frontend then redirects to login.

### 4.5 OTP Security Requirements

- Cryptographically secure generation
- 6 digits
- ~10 minute expiry
- Maximum verification attempts (then lock out / require a new OTP)
- Resend cooldown (e.g. 60 seconds)
- Per-email **and** per-IP rate limiting
- Invalidate immediately after successful use
- Never store OTPs in plaintext
- Always return generic responses that don't reveal account existence
- All limits configurable via environment variables

### 4.6 Google Sign-In

```
Login page → "Sign in with Google" → Google authorization
  → Google returns auth response → Backend verifies identity
  → Find existing user by verified email or Google subject ID
  → Create user if new → Create authenticated session → Redirect to frontend
```

Requirements:
- Use Google's official OAuth 2.0 flow with a registered redirect URI
- Store the Google client ID/secret only on the backend (secrets manager / env vars) — **never** expose the client secret to the frontend
- Verify the Google identity **server-side**
- Use the verified email from the identity provider; store the Google subject ID
- Link Google login to an existing email/password account when the verified email matches
- Never create duplicate user rows for the same person

---

## 5A. Frontend Pages to Build (Forgot Password Flow)

Build these as **real routed pages**, not a single page with hidden steps or a static demo. Reuse existing IIChE styling/components wherever possible.

| Page | Route (suggested) | Fields / states | Backend endpoint | On success |
|---|---|---|---|---|
| 1. Forgot Password | `/forgot-password` | Email input · Send OTP button · loading state · generic success message · error handling | `POST /api/v1/auth/forgot-password/request` | Navigate to `/verify-otp`, carry the email forward |
| 2. OTP Verification | `/verify-otp` | OTP input · Verify button · Resend button + cooldown timer · invalid/expired/max-attempts states | `POST /api/v1/auth/forgot-password/verify-otp` | Store the returned `reset_token` in memory, navigate to `/reset-password` |
| 3. Create New Password | `/reset-password` | New password · Confirm password · strength validation · mismatch validation · loading/error states | `POST /api/v1/auth/forgot-password/reset` | Navigate to `/reset-password/success` |
| 4. Password Reset Success | `/reset-password/success` | Confirmation message · "Back to Login" button | — | User logs in with the new password |

Add a **"Forgot Password?"** link on the existing Login page routing to `/forgot-password`.

---

## 5B. Connecting Frontend ↔ Backend

Give the coding assistant explicit instructions so nothing is left half-wired:

1. **Base API URL** — Store the backend URL in a frontend env var (e.g. `VITE_API_URL`). Use one shared API client module for all requests.
2. **Session handling** — Prefer secure HttpOnly cookies set by the backend over manually managing bearer tokens in frontend state. If the backend uses cookie sessions, the frontend fetch/axios client must send credentials (`credentials: 'include'`).
3. **CORS** — FastAPI must explicitly allow the deployed frontend origin (and `http://localhost:5173` for local dev) via `CORSMiddleware`. Never use `allow_origins=["*"]` for authenticated production APIs. This is the most common reason a working backend appears "disconnected" from the frontend.
4. **CSRF protection** — Because this uses cookie-based authentication, add CSRF protection on state-changing endpoints (e.g. double-submit cookie or a CSRF token header).
5. **Login/signup wiring** — Connect existing fields to `POST /api/v1/auth/login` and `POST /api/v1/auth/signup`. Add the Forgot Password link per Section 5A.
6. **Google Sign-In button** — On click, redirect to `GET /api/v1/auth/google/login`. After Google redirects to `GET /api/v1/auth/google/callback`, the backend establishes the session and redirects the browser to a frontend route (e.g. `/auth/callback`), which then calls `GET /api/v1/auth/me` to load the user.
7. **Protected routes** — Wrap events dashboard, registration flow, "my registrations," and admin dashboard in a route guard that calls `GET /api/v1/auth/me` on load and redirects unauthenticated users to `/login`.
8. **Required frontend states** — Every auth-related page must visibly handle: loading, success, invalid credentials, network error, email already exists, weak password, password mismatch, OTP sent, OTP expired, invalid OTP, too many OTP attempts, OTP resend cooldown, password reset success, Google login failure, session expired. Never expose sensitive internal detail in these messages.
9. **Local dev setup** — FastAPI on one port (e.g. `:8000`), Vite frontend on another (e.g. `:5173`), with `VITE_API_URL` pointing at localhost in dev and the deployed backend URL in production.

---

## 6. Database Schema

### `users`
| Column | Notes |
|---|---|
| id | Primary key |
| full_name | |
| email | Unique |
| password_hash | Nullable (Google-only users) |
| google_subject_id | Unique when present |
| profile_image_url | Nullable |
| is_active | |
| is_email_verified | |
| role | `user` / `admin` — controlled values only |
| created_at / updated_at / last_login_at | |

Never trust a role sent from the frontend — authorization is always resolved server-side from this table.

### `events`
| Column | Notes |
|---|---|
| id | Primary key |
| title, description | |
| event_date | |
| registration_deadline | |
| venue | |
| capacity | |
| is_active | |
| created_at / updated_at | |
| *(optional)* banner_image_url, organizer, event_category, registration_open | |

### `registrations`
| Column | Notes |
|---|---|
| id | Primary key |
| user_id | FK |
| event_id | FK |
| registered_at | |
| status | |

**Critical constraint:** `UNIQUE(user_id, event_id)` — prevents a user from registering for the same event twice, even under rapid double-clicks or race conditions.

**Indexes:** `users.email`, `users.google_subject_id`, `events.event_date`, `registrations.user_id`, `registrations.event_id`, composite `(user_id, event_id)`, plus composite indexes for frequent admin queries.

### `password_reset_otps` (or Redis-backed equivalent)
| Column | Notes |
|---|---|
| id | Primary key |
| user_id | FK |
| otp_hash | Hashed, never plaintext |
| expires_at | ~10 minutes |
| is_used | |
| attempt_count | For max-attempts enforcement |
| created_at | |

---

## 7. Event Registration Flow (Concurrency-Safe)

> **Current phase note:** Build this entire flow now — model, endpoint, constraints, admin views — but it stays **gated off** on the live site until IIChE has a real event ready to accept registrations. See Section 22 for exactly how the gating works. Do not skip building this because "there's nothing to register for right now" — the goal is that when the first real event goes live, IIChE just flips a flag, with no last-minute backend work and no risk of the site breaking under load.

```
Frontend: POST /api/v1/events/{event_id}/register

Backend:
  1. Authenticate the user.
  2. Confirm the event exists and is active.
  3. Check the registration deadline.
  4. Check capacity.
  5. Check whether the user already registered.
  6. Create the registration inside a transaction.
  7. Return success.
```

**This must be transaction-safe.** Consider: User A double-clicks Register, and User B registers for the same last slot at the same instant. The database — not frontend JavaScript — must guarantee:
- One registration per user per event (`UNIQUE(user_id, event_id)`)
- Event capacity is never exceeded, even under concurrent requests (use a transaction / row locking / an atomic capacity check)
- Duplicate rapid requests never create duplicate rows

Also provide:
```
GET /api/v1/users/me/registrations
```
For "My Events" / upcoming / past / registration status views.

---

## 8. Admin Functionality

IIChE admins get protected admin-only APIs (require `role = admin`, checked server-side):

```
GET    /api/v1/admin/events
POST   /api/v1/admin/events
PATCH  /api/v1/admin/events/{event_id}
DELETE /api/v1/admin/events/{event_id}
GET    /api/v1/admin/events/{event_id}/registrations
GET    /api/v1/admin/events/{event_id}/registrations/export
```

Admin frontend (can come later): event creation/editing, registration counts, registered-user lists, search/filtering, CSV export. Never expose the full user list to non-admin users.

---

## 9. Full API List (Versioned)

Use `/api/v1/...` for everything — never ship an unversioned API that becomes hard to evolve.

```
Auth:
POST   /api/v1/auth/signup
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
GET    /api/v1/auth/me

Google:
GET    /api/v1/auth/google/login
GET    /api/v1/auth/google/callback

Password reset:
POST   /api/v1/auth/forgot-password/request
POST   /api/v1/auth/forgot-password/verify-otp
POST   /api/v1/auth/forgot-password/reset

Users:
GET    /api/v1/users/me
GET    /api/v1/users/me/registrations

Events:
GET    /api/v1/events
GET    /api/v1/events/{event_id}

Registrations:
POST   /api/v1/events/{event_id}/register
DELETE /api/v1/events/{event_id}/register

Admin:
GET    /api/v1/admin/events
POST   /api/v1/admin/events
PATCH  /api/v1/admin/events/{event_id}
DELETE /api/v1/admin/events/{event_id}
GET    /api/v1/admin/events/{event_id}/registrations
GET    /api/v1/admin/events/{event_id}/registrations/export

Infrastructure:
GET    /health
GET    /ready
```

`/health` returns basic liveness. `/ready` checks that required dependencies (DB, Redis) are reachable — used by load balancers/orchestration. Neither should expose sensitive infrastructure details.

---

## 10. Sizing the System — "500 Users" ≠ "500 req/s"

A 500 req/s target is a **performance target**, not a user count — 500 registered users does not automatically mean 500 requests/second. Still, design so a load test can approach that target.

### Recommended starting production architecture

```
                        Users
                          |
                          v
                Cloudflare / CDN / WAF
                          |
                          v
                    Load Balancer
                          |
             +------------+------------+
             |            |            |
             v            v            v
          FastAPI      FastAPI      FastAPI
          replica 1    replica 2    replica 3
             |            |            |
             +------------+------------+
                          |
              +-----------+-----------+
              |                       |
              v                       v
           Redis                 PostgreSQL
              |
       OTP / rate limits
                          |
                          v
                  Email Provider
```

- Start with **2–3 FastAPI replicas** (async, stateless containers) if the hosting platform supports it.
- **Do not assume a fixed server count guarantees 500 RPS** — measure with real load tests. Actual capacity depends on endpoint logic, DB queries, network latency, CPU/memory, and connection limits.
- **PostgreSQL performance:** connection pooling (e.g. PgBouncer), proper indexes (listed in Section 6), efficient/paginated queries, transactions where required, query logging during perf tests, managed backups, monitoring. Avoid N+1 query patterns in admin dashboards.
- **Connection pooling matters especially with multiple replicas** — each replica opening unlimited DB connections will exhaust PostgreSQL's connection capacity. Route through a pooler.
- FastAPI containers must remain **stateless** — session state lives in the shared database/Redis, not in a single process's memory, so any replica can serve any request.

---

## 11. Where Docker, Redis, CDN, and Kubernetes Fit

| Tool | Purpose | Needed now? |
|---|---|---|
| **Docker** | Packages the app + Python + dependencies into a portable image; container should be stateless (no user uploads or DB files inside it) | Yes, once the backend is functional |
| **Redis** | Rate limiting, OTP attempt/cooldown state, temporary OAuth state — ephemeral shared state only, never the source of truth | Yes — needed for correct multi-replica rate limiting/OTP behavior |
| **CDN (Cloudflare)** | DNS, TLS, DDoS protection, WAF, static asset caching. **Never cache** `/auth/me`, `/auth/login`, `/auth/logout`, `/forgot-password/*`, `/register`, or admin APIs unless a deliberate, security-reviewed policy exists | Yes — cheap win for static assets + edge protection |
| **Kubernetes** | Full container orchestration (Deployments, Services, Ingress, autoscaling) | **Not needed** at ~500 users / 500 RPS — adds cluster/networking complexity without real benefit yet |

**Local dev** can run FastAPI + PostgreSQL + Redis together via Docker Compose. **Production** should use managed PostgreSQL and managed Redis rather than running stateful services inside the application host.

**Kubernetes migration path (later, only if justified):**
```
Stage 1: Frontend + FastAPI + managed PostgreSQL + Redis + Docker + CI/CD
Stage 2: Add load testing, observability, multiple replicas, automated rollback, better caching
Stage 3 (only if traffic/ops genuinely require it):
  Docker image → Kubernetes Deployment → HorizontalPodAutoscaler → multiple FastAPI pods
```

---

## 12. Security Checklist

- HTTPS everywhere in production
- Secure, HttpOnly, SameSite session cookies
- Argon2id password hashing (never plaintext)
- Input validation on every request (Pydantic schemas)
- SQL injection protection via SQLAlchemy parameterization
- CORS restricted to the exact real frontend origin — never `*` for authenticated APIs
- CSRF protection wherever cookie-based auth requires it
- Rate limiting on authentication and password-reset endpoints (via Redis)
- Request size limits
- Security headers at the edge/reverse proxy
- Secrets in environment variables or a secrets manager — never committed to Git
- Generic error messages on auth endpoints to prevent account enumeration
- Logging that never includes passwords, OTPs, session secrets, or OAuth client secrets
- Database backups
- Dependency updates / vulnerability scanning
- Server-side admin authorization checks on every admin endpoint
- Hashed, expiring, single-use OTPs; invalidate old sessions after a password reset
- `UNIQUE(user_id, event_id)` DB constraint as the real backstop against duplicate registrations

---

## 13. Observability

Add: structured logs, request IDs, error tracking, metrics, DB performance monitoring, container health monitoring, authentication event logging, admin action logging.

Monitor: request latency, requests/sec, error rate, CPU, memory, DB connections, DB query latency, Redis latency, auth failure rate, OTP delivery failure rate, registration success/failure rate.

**Never log:** passwords, OTP values, authentication cookies, session secrets, OAuth client secrets.

---

## 14. Load Testing

Before claiming the system handles 500 RPS, run a real load test (k6, Locust, or JMeter) against:
1. Public event listing
2. Login
3. Authenticated `/me`
4. Event registration (special attention — it writes to Postgres under uniqueness/capacity constraints)
5. Admin registration listing

Measure: RPS, P50/P95/P99 latency, error rate, CPU, memory, PostgreSQL CPU/connections, Redis performance.

---

## 15. Testing Strategy

Minimum automated test coverage:

- **Signup:** valid account, duplicate email, invalid email, password mismatch, weak password
- **Login:** correct password, incorrect password, unknown email, inactive account
- **Password reset:** OTP generation, expiration, incorrect OTP, too many attempts, correct OTP, reset success, token invalidation, login with new password
- **Google:** valid callback, invalid callback, existing-account linking, new account creation, invalid state
- **Events:** public listing, admin creation/edit, unauthorized admin access rejected
- **Registration:** authenticated registration, unauthenticated rejection, duplicate rejection, closed-event rejection, full-event rejection, concurrent registration behavior

---

## 16. Suggested Backend Project Structure

```
backend/
  app/
    main.py
    api/
      v1/
        auth.py
        users.py
        events.py
        registrations.py
        admin.py
    core/
      config.py
      security.py
      logging.py
    db/
      session.py
      base.py
    models/
      user.py
      event.py
      registration.py
      otp.py
    schemas/
      auth.py
      user.py
      event.py
      registration.py
    services/
      auth_service.py
      google_auth_service.py
      otp_service.py
      email_service.py
      event_service.py
      registration_service.py
    repositories/
      user_repository.py
      event_repository.py
      registration_repository.py
    middleware/
      rate_limit.py
      request_id.py
    tests/
      test_auth.py
      test_password_reset.py
      test_google_auth.py
      test_events.py
      test_registrations.py
  alembic/
  alembic.ini
  Dockerfile
  docker-compose.yml
  requirements.txt
  .env.example
  README.md
```

Keep routers thin — put business logic in `services/`, keep data access in `repositories/`, validate everything with Pydantic `schemas/`.

---

## 17. Environment Variables (`.env.example`)

```
DATABASE_URL=
REDIS_URL=
FRONTEND_URL=
BACKEND_URL=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=

EMAIL_PROVIDER_API_KEY=
EMAIL_FROM_ADDRESS=

SESSION_SECRET=
CSRF_SECRET=

OTP_EXPIRY_SECONDS=600
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_ATTEMPTS=5

RATE_LIMIT_LOGIN=
RATE_LIMIT_PASSWORD_RESET=
```

Never commit `.env`. All production secrets go through the deployment platform's secret manager.

---

## 18. CI/CD

```
Developer pushes code → GitHub → CI
  → install deps → lint → type checks → unit tests → integration tests → dependency/security checks
  → build Docker image → push to container registry
  → deploy backend → run DB migration → health check → deployment complete
```

Never auto-run destructive production migrations. Migrations (via Alembic) should be backward-compatible: change model → generate migration → review → test → apply.

---

## 19. Recommended Build Order

**Phase 1** — FastAPI project, PostgreSQL + SQLAlchemy + Alembic, user model, signup, password hashing, login, logout, `/auth/me`

**Phase 2** — Password reset: OTP service, email provider integration, reset-token flow, rate limiting

**Phase 3** — Google OAuth, account linking, session hardening

**Phase 4** — Event model, event APIs, registration model, register endpoint, "my registrations"

**Phase 5** — Admin authorization, admin event management, registration dashboard, CSV export

**Phase 6** — Docker, CI/CD, production secrets, managed PostgreSQL, Redis, Cloudflare/WAF, monitoring, backups

**Phase 7** — Load testing, database optimization, horizontal backend replicas, production hardening

**Phase 8** — Kubernetes only if traffic and operational requirements actually justify it

---

## 20. Important Implementation Rules for Antigravity

Treat this as a **full-stack integration task**, not an isolated backend build:

- Do not build FastAPI as a standalone project disconnected from the frontend.
- Do not leave the current frontend wired to mock APIs.
- Do not leave authentication as frontend-only fake state.

**Before writing any backend code, first inspect the existing frontend completely** and identify:
- Framework and package manager
- Existing routes
- Login page components
- Create Account page
- Existing Forgot Password entry point
- Google login button
- Event pages and Register buttons
- Existing state management and API utility files
- Existing environment configuration
- Any existing Supabase/Firebase/other backend code
- Existing styling, animations, components, and design tokens

Then:
- **Reuse working frontend components** wherever possible.
- **Preserve the current IIChE visual design** — do not remove working animations/styling, do not redesign the login page unless a functional requirement forces a small change.
- Implement the FastAPI backend, then connect the *existing* frontend to the *real* backend.

### 20.1 Engineering Rules

1. Backend is the source of truth for authentication and authorization.
2. PostgreSQL is the source of truth for permanent user, event, and registration data.
3. Redis is only for temporary/shared high-speed state (rate limits, OTP state) — never permanent data.
4. Frontend never connects directly to PostgreSQL.
5. Never store plaintext passwords.
6. Never put backend secrets in frontend code.
7. Never trust role information sent from the browser.
8. Database constraints enforce critical uniqueness rules — don't rely on frontend logic alone.
9. Authentication must work correctly across multiple FastAPI replicas (stateless containers, shared DB/Redis).
10. Every protected endpoint performs server-side authorization.
11. Use migrations (Alembic) for all schema changes.
12. Write automated tests before major deployment changes.
13. Measure performance before adding infrastructure complexity.
14. Don't introduce Kubernetes unless the real operational requirement justifies it.

### 20.2 Required End-to-End Verification

Antigravity must test these complete flows in the browser against the real backend and real PostgreSQL — not mocked:

**Email account flow:** Create Account → user row created in PostgreSQL → Login → authenticated session → refresh browser (session persists per policy) → open Events → Register → registration row created → Logout → Login again.

**Forgot password flow:** Forgot Password → enter email → OTP emailed → OTP Verification page → verify → Create New Password page → password updated → Password Reset Success page → login with new password.

**Google flow:** Login page → Sign in with Google → Google authorization → backend verifies identity → session created → Events page → Register.

Do not mark the implementation complete until frontend and backend work together end to end on all three flows.

---

## 21. Definition of Done

The implementation is not complete until **all** of the following are true:

- Existing login UI works with email and password
- Create Account works
- Password hashes are stored securely (Argon2id)
- Logout works, and the user can log in again afterward
- Forgot Password sends an OTP to the user's email
- OTP verification page works correctly
- New password page resets the password
- The old reset token becomes invalid after use
- The new password logs the user in
- Google Sign-In works and stores Google user data correctly
- Authenticated state persists per the chosen session strategy
- PostgreSQL stores users, events, and registrations
- Duplicate registrations are prevented at the database level
- Admin can view event registrations
- Authorization is enforced server-side everywhere
- Rate limits exist on sensitive endpoints
- CORS is restricted to the real frontend origin
- No secrets are committed to Git
- Docker build works
- CI tests pass
- Production deployment works
- `/health` and `/ready` endpoints work
- Database migrations work
- Backups are configured
- Load testing has been performed against the 500 RPS target
- Performance bottlenecks have been identified
- The production frontend remains visually consistent with the original IIChE design

---

## 22. Current Phase: Registration Feature Is Built, But Switched Off

**Context:** IIChE has no live event open for registration right now. The Register button must **not** be usable on the live site today. But the full registration system (database, APIs, admin views) should be built now, so that when a real event does go live, IIChE can just turn it on — no rushed backend work, no risk of the site crashing under sudden load from everyone registering at once.

This is a **feature flag**, not a missing feature. Nothing in Sections 6–8 changes — build all of it now.

### 22.1 How the gating works

Add a per-event flag (already listed as an optional column in Section 6):

```
events.registration_open   (boolean, default: false)
```

Rules:
- Every event defaults to `registration_open = false` when created.
- Only an admin can flip it to `true` for a specific event, via the existing admin event-edit endpoint (`PATCH /api/v1/admin/events/{event_id}`).
- The backend `POST /api/v1/events/{event_id}/register` endpoint must reject the request (clear error, e.g. "Registration is not open for this event yet") if `registration_open` is `false` — **even if someone calls the API directly**, bypassing the frontend. The backend is the real gate, not just the button state.
- There is no need for a *global* kill switch beyond this — an empty events list or all-events-closed naturally means registration is closed everywhere.

### 22.2 What the Events page shows right now

- The Events page itself stays live — visitors can browse events, see details, dates, venue, etc.
- The **Register button is not shown as a live, clickable action** while `registration_open` is `false`. Show it in a clearly disabled/inactive state (e.g. greyed out, label like "Registration opens soon") rather than hiding it entirely — this avoids a layout that has to be rebuilt later.
- No login is required just to browse events. Login is only required at the point of registering.

### 22.3 What happens once an event goes live (future state — build it now, don't wait to implement it later)

1. Admin flips `registration_open = true` for that event.
2. On the Events page, that event's Register button becomes active for logged-in users.
3. If a visitor who isn't logged in clicks Register, redirect them to login/signup first, then bring them back to the event.
4. Once a logged-in user successfully registers:
   - The backend creates the registration row (per the concurrency-safe flow in Section 7).
   - The frontend button switches to a confirmed/registered state — e.g. **turns green** with a label like "You're Registered ✓" — and that state persists (re-fetch registration status from the backend, don't just rely on local UI state, so it's correct even after a page refresh or on another device).
   - This status is also visible to the user on their "My Registrations" page (`GET /api/v1/users/me/registrations`).
5. The admin can see, per event, exactly who has registered (`GET /api/v1/admin/events/{event_id}/registrations`) and export the list (`.../export`) to help manage the event.

### 22.4 Why build it now instead of later

- The database schema, constraints (`UNIQUE(user_id, event_id)`, capacity checks), and concurrency-safe transaction logic are exactly the parts that are hardest to get right under pressure — building and testing them now, with no live traffic at stake, is much safer than building them the week an event is announced.
- Load testing the registration endpoint (Section 14) can happen now, in a low-stakes environment, well before real users ever hit it.
- When IIChE is ready for its first event, turning registration on should be a one-line admin action (flip `registration_open`), not a deployment.

---

## 23. Final Implementation Objective

Turn the existing IIChE frontend into a real full-stack application **without changing its visual identity**.

```
Open IIChE website → Create account or Sign in with Google → Authenticated user
  → Browse events → Press Register → Registration saved to PostgreSQL
  → IIChE admin can view attendee data
```

```
Forgot Password → Enter email → OTP sent to email → Enter OTP
  → Create new password → Password updated → Login with new password
```

The system should be secure, testable, maintainable, horizontally scalable, and no more complex than the current IIChE project actually needs.

- Build a solid modular FastAPI backend first — don't over-engineer the first deployment.
- Use Docker and CI/CD from the start if they don't slow development down.
- Use managed PostgreSQL and Redis in production.
- Use CDN/WAF at the edge.
- Load-test to validate the 500 RPS target before claiming it's met.
- Introduce Kubernetes only when real traffic, reliability, or operational needs justify it.
