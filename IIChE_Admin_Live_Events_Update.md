# IIChE Website — Admin Dashboard Fix & Live Event Management Spec

This document extends the earlier `IIChE_Website_Architecture.md` spec. It does **not** replace it — the auth system, database, security rules, and general architecture from that document still apply. This file covers a focused set of changes:

1. Fix the admin dashboard's buffering/loading bug
2. Make the admin registration dashboard real-time and precise (accounts view + per-event view)
3. Add CSV export of registration data
4. Connect the admin "Add Event" form directly to the public Events page
5. Make each event card's button (Coming Soon → Register → Registered → Closed) update itself automatically based on admin input and time
6. Gate registration behind login, with a smooth "log in → land back on the event" flow

Everything here must be built **without slowing the website down**. Section 11 covers the performance rules explicitly — read it before implementing the "real-time" pieces.

---

## 1. Current Problems to Fix

- The admin dashboard currently shows a **loading/buffering state that doesn't resolve properly** — this is a bug, not a missing feature, and must be root-caused, not just hidden with a longer spinner.
- The registration tab is **not actually connected to live database data** — it needs to show real registrants, not stale or mock data.
- Admin cannot currently see registration data broken out in the two views IIChE actually needs (see Section 2).
- There is no CSV export yet.
- The "Add Event" admin form does not currently affect the public Events page — cards are static with a hardcoded "Coming Soon" button.
- There is no logic that flips a card from "Coming Soon" to "Register" when an admin publishes an event, or from "Register" to closed after the deadline passes.

---

## 2. Fix the Admin Dashboard Buffering Bug

Before adding new features, diagnose and fix the existing bug. Antigravity should work through this checklist and identify the actual root cause rather than papering over it:

**Backend-side checks**
- Is the dashboard's data endpoint actually returning a response, or hanging? Check for a missing `await`, an unclosed DB session, or a query with no timeout that's stuck waiting on a lock.
- Is the endpoint doing an unpaginated `SELECT *` across all registrations/users? At even a few hundred rows this can look fine locally and slow down badly once real data or joins are involved — this is the most common cause of a dashboard that "spins forever."
- Are there N+1 queries — e.g. fetching all events, then looping and querying registrations per event one at a time? Replace with a single joined/aggregated query.
- Is the request missing proper error handling, so a failed query just leaves the frontend waiting instead of returning an error the UI can show?
- Check actual server logs and response time for the dashboard endpoint(s) under real data, not just an empty dev database.

**Frontend-side checks**
- Is there a `fetch`/`axios` call with no timeout, so a slow or hung backend leaves the UI stuck on a loading spinner indefinitely?
- Is the dashboard waterfalling several sequential API calls (call 1 finishes, then call 2 starts, then call 3...) instead of firing them in parallel? This alone can look like buffering even when each call is individually fast.
- Is there a polling loop that keeps re-requesting without ever clearing its interval, piling up requests?
- Is the loading state tied to the wrong condition (e.g. never gets set back to `false` on error, only on success)?

**Fix requirements**
- Every dashboard data-fetching call must have a sensible timeout and a visible error state (not an infinite spinner) if it fails.
- Add basic request/response logging (with a request ID, see the observability section of the main spec) around the dashboard endpoints so future issues are diagnosable quickly.
- Confirm the fix by testing the dashboard against a database seeded with a realistic amount of data (multiple events, at least a few hundred registrations), not just one or two test rows.

---

## 3. Admin Dashboard: What It Must Show

Two distinct views, as you described:

### 3.1 View 1 — All Registered Accounts (Users Panel)

A list of every user who has signed up on the website (regardless of event registration), showing at minimum: name, email, signup method (email/password or Google), account created date, last login.

```
GET /api/v1/admin/users
```
- Paginated (never return the full table in one response).
- Searchable/filterable by name or email.
- Sortable by signup date.

### 3.2 View 2 — Per-Event Registrants (Events Panel)

For each event, the exact count and list of who registered — this is the "for this event, these many users are registered" view.

```
GET /api/v1/admin/events                              → list of events with a live registrant_count per event
GET /api/v1/admin/events/{event_id}/registrations      → paginated list of registrants for that specific event
```
- The events list view should show, per event: title, date, registration status (open/closed/coming soon), and a live `registrant_count`.
- Clicking into an event shows the full registrant list (name, email, registered_at timestamp).

### 3.3 CSV Export

Two export options, matching the two views above:

```
GET /api/v1/admin/users/export                                → CSV of all registered accounts
GET /api/v1/admin/events/{event_id}/registrations/export      → CSV of registrants for one specific event
```

Requirements:
- Generate the CSV **server-side**, streamed directly from the database query — do not load the full dataset into memory first if it can be avoided, and do not generate it client-side from an already-fetched JSON blob (that duplicates data transfer and doesn't scale).
- Response headers should trigger a direct file download in the browser (`Content-Disposition: attachment; filename=...`).
- Only accessible to authenticated admins — enforce the same server-side role check as every other admin endpoint.

### 3.4 Making This "Real-Time" Without Slowing the Site Down

"Real-time" here should mean **the admin sees current data within a few seconds of opening or refreshing the dashboard**, not a permanently open firehose connection that adds constant load. Two acceptable approaches, in order of preference for this project's scale:

**Preferred: short polling + server-side caching**
- Frontend re-fetches dashboard summary data on a reasonable interval (e.g. every 10–15 seconds) while the admin has the dashboard open, and pauses when the tab isn't visible (use the Page Visibility API).
- Backend caches expensive aggregate queries (like per-event registrant counts) in Redis for a few seconds, so a burst of dashboard refreshes doesn't hit PostgreSQL directly every time.
- This is simple, cheap, reliable, and matches the actual need — the admin doesn't need millisecond-level updates.

**Optional upgrade later: Server-Sent Events (SSE) or WebSocket push**
- If truly instant updates become important later (e.g. watching registrations come in live during a big event), the backend can publish registration events to a Redis pub/sub channel and push them to connected admin dashboards via SSE/WebSocket instead of polling.
- Don't build this now — it adds real complexity for a benefit the current use case doesn't need yet. Polling + caching is the right choice for launch.

Either way: **the public-facing Events page and registration flow must never be slowed down by admin dashboard activity.** Keep admin aggregate queries separate from the hot path a regular user hits when registering.

---

## 4. Admin "Add Event" → Public Events Page

The admin's "Add Event" form must directly control what appears on the public Events page — there should be no manual step to "publish" a card separately from the data.

### 4.1 Admin Add/Edit Event Form Fields

- Title
- Category
- Description
- Date and time of the event
- Venue
- Registration deadline (date + time)
- Capacity (optional)
- Status: **Draft** or **Published**

### 4.2 How It Connects to the Public Page

```
Admin fills form → POST /api/v1/admin/events (status: draft or published)
  ↓
Event stored in `events` table
  ↓
Public GET /api/v1/events reads directly from the same table
  ↓
Public Events page re-fetches and renders the updated card — no separate sync step, no redeploy
```

- A **Draft** event is saved but not shown on the public Events page at all (useful for events the admin is still preparing).
- A **Published** event immediately appears as a real card on the public Events page, with its button state computed as described in Section 5.
- Editing an already-published event (e.g. fixing a typo, changing the deadline) should update the live card the next time the page loads — no caching layer should hold onto stale event data for more than a few seconds (short TTL cache at most, same Redis approach as Section 3.4, if caching is used at all here).

---

## 5. Event Card Button State — Computed, Not Manually Toggled

Rather than a separate on/off switch the admin has to remember to flip, the button state should be **derived automatically** from data that's already on the event: `status` (draft/published) and `registration_deadline`. This avoids the button getting out of sync with reality.

### 5.1 States

| Condition | Card shows |
|---|---|
| Event `status = draft` | **Coming Soon** (button disabled/inactive) |
| Event `status = published` AND now < `registration_deadline` | **Register** (active button) |
| Event `status = published` AND user is logged in AND already registered for this event | **Registered ✓** (green, disabled — see main spec Section 22.3) |
| Event `status = published` AND now ≥ `registration_deadline` | **Registration Closed** (see note below) |

**Note on the "back to Coming Soon" request:** you described the button reverting to "Coming Soon" after the deadline passes. Functionally that's easy to do (see 5.2), but it's worth flagging: "Coming Soon" and "Registration Closed" mean different things to a visitor — "Coming Soon" reads as *not open yet*, which could confuse someone about whether the event already happened. **Recommended default:** show "Registration Closed" (or "Event Ended" if the event date has also passed) after the deadline, and reserve "Coming Soon" for events still in draft. If you'd still rather literally reuse the "Coming Soon" label after the deadline, that's a one-line label change in the frontend component — the underlying logic is identical either way, so build it with the label as a simple configurable string rather than hardcoded, and pick whichever fits IIChE's branding once you see it live.

### 5.2 Implementation Approach

Compute the display status **at read time**, in the API response — don't store a `button_state` column that has to be kept in sync by a background job:

```
GET /api/v1/events → each event includes a computed field, e.g. "registration_status": "coming_soon" | "open" | "closed"
```

This is calculated in the backend from `status` + `registration_deadline` vs. the current server time on every request. It's always correct, requires no cron job, and can't drift out of sync.

The frontend maps `registration_status` (and, for logged-in users, their own registration record) directly to the card's button label, color, and enabled/disabled state.

---

## 6. Login-Gated Registration Flow From the Event Card

```
Visitor sees a Published event card with an active "Register" button
  ↓
Clicks Register
  ↓
Is the visitor logged in?
  ├── No  → redirect to /login (or /signup, based on which the user picks),
  │         carrying a "return to" reference to this specific event
  │         → user logs in or creates an account
  │         → on success, redirect back to the Events page, scrolled/linked to that event
  │         → user clicks Register again (or, if you want to save them the extra click,
  │            automatically complete the registration immediately after login using the
  │            saved "return to" reference — either is acceptable; auto-complete is a nicer
  │            UX but must still re-run every backend check in Section 7 of the main spec
  │            before creating the registration)
  │
  └── Yes → call POST /api/v1/events/{event_id}/register directly
             → backend re-validates: published, before deadline, not already registered, capacity
             → on success, button turns green / "Registered ✓"
```

Implementation notes:
- Store the "return to event" reference as a query param or short-lived value in frontend routing state — never trust it as an authorization mechanism, it's purely for UX redirection.
- The backend registration endpoint must independently re-check everything (login state, event status, deadline, duplicate, capacity) regardless of what the frontend already checked — this matches the "backend is the real gate" rule from the main spec.

---

## 7. API Endpoints Summary (New/Updated)

```
Admin — users:
GET    /api/v1/admin/users
GET    /api/v1/admin/users/export

Admin — events:
GET    /api/v1/admin/events                              (includes live registrant_count + registration_status per event)
POST   /api/v1/admin/events                               (create, status: draft|published)
PATCH  /api/v1/admin/events/{event_id}                    (edit fields, change status, change deadline)
DELETE /api/v1/admin/events/{event_id}
GET    /api/v1/admin/events/{event_id}/registrations
GET    /api/v1/admin/events/{event_id}/registrations/export

Public:
GET    /api/v1/events                                     (published events only, each with computed registration_status)
GET    /api/v1/events/{event_id}
POST   /api/v1/events/{event_id}/register
GET    /api/v1/users/me/registrations
```

All admin endpoints require server-side role verification (`role = admin`) on every call — never inferred from the frontend.

---

## 8. Database Schema Updates

Building on the `events` table from the main spec:

### `events` (updated)
| Column | Notes |
|---|---|
| id | Primary key |
| title, category, description | |
| event_date | |
| venue | |
| registration_deadline | Used to compute `registration_status` |
| capacity | |
| status | `draft` \| `published` — controls public visibility |
| created_by | FK → admin user who created it |
| created_at / updated_at | |

`registration_open` from the earlier spec is effectively superseded by `status` + `registration_deadline` — the computed `registration_status` in Section 5.2 replaces the need for a separate manual flag. If you already built `registration_open` per the earlier spec, migrate it: `status = draft` if it was `false`, `status = published` if it was `true`, and add `registration_deadline` as the real gate going forward.

No structural change needed to `users` or `registrations` — the indexes and unique constraint from the main spec (`UNIQUE(user_id, event_id)`) still apply and remain the actual backstop against duplicate registrations.

---

## 9. Performance & Architecture Guardrails

These are non-negotiable — the whole point of this update is to make the admin/event system fast and correct, not to add something that makes the site slower:

1. **Every list endpoint is paginated.** No endpoint returns an entire table in one response — not the users list, not a registrants list.
2. **Aggregate counts (registrant_count per event) are computed with a single efficient query** (e.g. a `GROUP BY` or a materialized count), never by looping per event.
3. **Admin dashboard queries are isolated from the public registration hot path.** A slow admin report must never compete for the same connection pool slots as a user clicking Register.
4. **Cache expensive aggregate reads in Redis with a short TTL** (a few seconds) rather than hitting PostgreSQL on every dashboard poll.
5. **CSV exports stream from the database** rather than materializing the whole result set in memory first.
6. **The public Events page computes registration_status at read time** — no background cron job is required to "flip" buttons, which removes an entire class of drift/timing bugs.
7. **Every frontend data fetch has a timeout and a visible error state** — no call is allowed to leave the UI in an infinite loading spinner (this directly fixes the buffering bug in Section 2).
8. **Indexes required:** `registrations.event_id` (for per-event counts and lists), `registrations.user_id`, `events.status`, `events.registration_deadline`, `users.email`. Confirm these exist via `EXPLAIN ANALYZE` on the actual admin queries once real data is loaded.
9. **Load-test the admin dashboard and the CSV export** the same way the main spec calls for load-testing registration (Section 14 of the main spec) — a report screen that works fine with 10 rows can still be the thing that falls over first with real data.

---

## 10. Required End-to-End Verification

Test all of these against the real backend and real PostgreSQL data before calling this done:

1. **Admin dashboard loads without hanging**, even when seeded with multiple events and a realistic number of registrations.
2. **Users panel** shows every signed-up account, paginated, and the CSV export downloads a correct, complete file.
3. **Events panel** shows an accurate live registrant count per event; opening an event shows the correct registrant list; CSV export for a single event downloads correctly.
4. **Add Event (draft)** → confirm it does **not** appear on the public Events page.
5. **Add Event (published)**, deadline in the future → confirm the public card appears with an active **Register** button.
6. **Unauthenticated visitor** clicks Register → redirected to login/signup → completes it → lands back able to register for that specific event → registers → button turns green.
7. **Already-registered user** revisits the Events page (and after a refresh, and from another browser/device) → button correctly shows **Registered ✓**, not a plain Register button.
8. **Edit an event's deadline to a past time** → confirm the card automatically shows Registration Closed (or Coming Soon, per whichever label you choose in Section 5.2) with no manual admin action needed beyond the edit itself, and no code deploy required.
9. **Duplicate/rapid-click registration** on the same event by the same user → confirm only one registration row is created (`UNIQUE(user_id, event_id)` holds).
10. **Dashboard stays responsive** while a registration is actively being created — confirm admin traffic and public registration traffic don't block each other.

---

## 11. Definition of Done

- The admin dashboard buffering bug is fixed and root-caused, with a timeout + visible error state on every dashboard fetch.
- Admin can see all registered accounts (paginated) and export them as CSV.
- Admin can see, per event, an accurate live registrant count and full registrant list, and export any single event's registrants as CSV.
- Admin's Add Event form directly creates/updates rows in the same `events` table the public Events page reads from — no manual sync step.
- Draft events are invisible on the public page; published events appear automatically.
- Each event card's button state (Coming Soon / Register / Registered / Closed) is computed from `status` + `registration_deadline` + the current user's registration record — never manually toggled and never able to drift out of sync.
- Clicking Register while logged out sends the user through login/signup and back to the event, without losing their place.
- All new list/report endpoints are paginated, indexed, and isolated from the public registration hot path, per Section 9.
- Everything above has been verified end-to-end per Section 10, using realistic seeded data — not just one or two test rows.
