# Feature Spec: Recovery-Email-Verified Password Reset

## 1. Problem Statement

Currently, "Forgot Password" only requires the account's primary email. Since account
emails are often guessable or public, anyone who knows a user's email can trigger a
password reset and potentially take over the account (if they also have inbox access,
or if the OTP delivery/verification has any weakness).

**Fix:** Require a second, user-defined *recovery email* to be verified before an OTP
is even sent. The OTP is still delivered to the account's primary/registered email
(not the recovery email) — the recovery email is only used as a second knowledge
factor to prove the requester is the real account owner. This does not weaken
anything that currently exists; it only adds a gate before Step 1 of the existing flow.

> Do not change where the OTP is sent. Sending OTP to the recovery email instead of the
> registered email would be a *different* (weaker, phishable) design. Recovery email is
> a **verification factor**, the registered email remains the **delivery channel**.

---

## 2. Scope

- [ ] DB: add `recovery_email` field to the user/account table
- [ ] Signup: new field + validation + storage
- [ ] Forgot Password flow: insert a new first step (Recovery Email Verification) before OTP step
- [ ] Reuse existing OTP page and New Password page, but move them one step later
       in the flow (no new animation/design work needed — see Section 6)
- [ ] Update one line of copy on the existing "enter recovery email" page (already built)
- [ ] Backend: new endpoint to verify recovery email, rate limiting, audit logging

---

## 3. Database Changes

### 3.1 Schema migration

Add to the `users` table (or equivalent):

| Column | Type | Constraints |
|---|---|---|
| `recovery_email` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` per user optional, must be **different from** `email` (registered email) |
| `recovery_email_verified_at` | `TIMESTAMP` | nullable — set at signup if you auto-verify, or after a confirmation link/OTP if you want extra rigor |

**Rules to enforce at DB/application level:**
- `recovery_email` must not equal `email` (case-insensitive compare). Reject signup if they match — a recovery email that's identical to the login email defeats the whole purpose.
- Store recovery email in lowercase, trimmed, same normalization rules you already use for `email`.
- Do NOT make `recovery_email` globally unique across all users unless your product wants to forbid one person from using the same recovery inbox for multiple accounts — this is a product decision, default to **not globally unique**.

### 3.2 Migration safety for existing users

You already have existing accounts without a `recovery_email`. Decide one of:

- **Option A (recommended):** Make the column nullable initially. On next login (or via a forced "Add recovery email" prompt/banner), require existing users to set one before they can use Forgot Password. Until then, Forgot Password shows: *"You haven't set a recovery email yet. Please log in and add one from Account Settings, or contact support."*
- **Option B:** Force-migrate via a one-time email campaign asking users to set a recovery email within X days.

Do not silently allow Forgot Password to fall back to the old (insecure) single-email flow for users without a recovery email — that reopens the exact hole you're closing.

---

## 4. Signup Flow Changes

Add **one new field** to the Create Account form, after the primary email field:

- Label: `Recovery Email`
- Helper text: `"We'll use this to verify it's really you if you ever need to reset your password."`
- Validation:
  - Valid email format
  - Must NOT equal the primary account email (show inline error: `"Recovery email must be different from your account email."`)
  - Required (not optional) — do not let users skip this, or you're back to Option A migration logic for new signups too
- On submit: store `recovery_email` (normalized) alongside the rest of the new user record in the same transaction as user creation. No separate API call — one atomic create.

No new animations needed here — just extend the existing Create Account form/card with one more input using the same input component/styling already used for the other fields.

---

## 5. New Forgot Password Flow (Step-by-Step)

### Old flow:
```
[Enter Registered Email] → [Enter OTP] → [New Password + Confirm]
```

### New flow:
```
[Enter Registered Email]
        ↓
[Enter Recovery Email]  ← NEW STEP
        ↓ (only if match)
[Enter OTP]              ← existing page, unchanged UI, just reordered
        ↓ (only if OTP correct)
[New Password + Confirm] ← existing page, unchanged UI
```

### 5.1 Step 1 — Enter Registered Email (existing, unchanged)
User enters the account's primary email. On submit, do **not** reveal whether the
email exists (avoid user enumeration). Proceed to Step 2 regardless, OR if you already
reveal existence today, keep current behavior — just don't send an OTP yet either way.

### 5.2 Step 2 — Enter Recovery Email (NEW — reuse existing recovery-email page's design)

This page already exists in your product with the following copy that needs to
change:

**Current copy (replace this):**
> "Enter your registered email address below. We'll verify your registered account and send a 6-digit OTP code to reset your password."

**New copy (use this exact text):**
> "Enter your recovery email address below. We'll verify your registered account and send a 6-digit OTP code to reset your password."

Behavior:
- User submits a recovery email.
- Backend compares it (normalized, case-insensitive) against the `recovery_email` stored for the account identified in Step 1.
- **Match:** proceed to Step 3, backend generates and sends OTP to the account's *registered/primary* email (not the recovery email).
- **No match:** show inline error / toast: `"Wrong recovery email. Please try again."` Do NOT specify what the correct one is. Do NOT say "no recovery email set" vs "wrong email" as two different messages — use one generic message for both cases so an attacker can't use the error to fingerprint accounts.
- **Rate limit this step** (see Section 7) — this is the new attack surface (someone guessing recovery emails).

### 5.3 Step 3 — Enter OTP (existing page, reuse 100%)

- **No UI changes.** Same card style, same background, same cursor-follow/card-tilt animation, same layout, same "Enter OTP" copy.
- Only change: this step now only becomes reachable after Step 2 succeeds, and the OTP is generated/sent at the *end* of Step 2 instead of at the end of Step 1.
- OTP validation logic (expiry, attempt limits, resend cooldown) stays exactly as it is today.

### 5.4 Step 4 — New Password + Confirm Password (existing page, reuse 100%)

- **No UI changes.** Same animated card/background as the rest of the flow.
- Keep existing password requirements copy exactly as-is:

```
Password Requirements:
- At least 8 characters long
- Contains at least 1 uppercase letter (A-Z)
- Contains at least 1 lowercase letter (a-z)
- Contains at least 1 number (0-9)
```

- On submit: validate both fields match, validate against the rules above (client-side for UX + server-side as source of truth), then call the existing "update password" API — no change to that API's contract.

---

## 6. Frontend / Animation Requirements (Important)

You explicitly do not want new visual work for the OTP and New Password pages — and
you shouldn't need any:

- **Do not rebuild** the OTP page or the New Password page. Reuse the existing components/pages as-is.
- The only *new* frontend page is the Recovery Email step — and it already exists in the product, so this is a **copy-text change only** (Section 5.2), not new component work.
- The card style, cursor-follow/tilt animation, and background must come from the **same shared component** used by the other steps in this wizard (e.g. a shared `<AuthCard>` / `<AnimatedFormCard>` wrapper) so behavior stays visually identical automatically. If today each page duplicates its own animation code instead of using a shared component, that's worth refactoring into a shared component now — it removes drift risk and is exactly the kind of low-risk cleanup that pays off here.
- Simply **re-order the routes/steps** in the wizard's state machine so Recovery Email sits between Registered Email and OTP. Do not touch the OTP/New Password components themselves.

---

## 7. Backend / API Changes

### 7.1 New endpoint

```
POST /api/auth/forgot-password/verify-recovery-email
Body: { "resetSessionToken": "...", "recoveryEmail": "..." }
Response: { "success": true }  // or 400 with generic error
```

- `resetSessionToken` should be the same short-lived session/state token issued after Step 1 (registered email submitted), so this endpoint knows *which* account to check against without trusting a raw email/user-id from the client.
- On success, this endpoint is what triggers OTP generation + send (move this trigger from the old Step 1 endpoint to here).

### 7.2 Existing endpoints to adjust

- **Step 1 endpoint** (`/forgot-password/request` or equivalent): stop sending OTP here. Instead, issue/refresh the `resetSessionToken` and move to Step 2.
- **OTP verify endpoint**: unchanged logic, just confirm it still uses the same `resetSessionToken` / session continuity so Steps 2→3→4 can't be skipped by hitting the OTP or update-password endpoints directly out of order.
- **Update password endpoint**: unchanged, but double check it still requires a valid, OTP-verified session token — don't let it be called directly with just an email.

### 7.3 Session/state integrity (critical)

Make sure the whole 4-step wizard is backed by **one server-side session/token** that
gets upgraded at each step (e.g. `email_submitted → recovery_verified → otp_verified → allowed_to_reset`), and every endpoint checks the current stage server-side. This is what actually prevents someone from skipping Step 2 (recovery email check) by calling
the OTP or password-update endpoints directly.

### 7.4 Security / rate limiting

- Rate-limit Step 2 (recovery email guesses) per account and per IP — e.g. 5 attempts / 15 min, then temporary lockout of that reset session. This is the main new abuse vector you're introducing (attacker can now brute-force guess a recovery email instead of triggering OTP straight away), so it needs its own limiter, separate from the existing OTP rate limit.
- Log failed recovery-email attempts (account id, IP, timestamp) for audit/anomaly detection, without logging the guessed email in plaintext if you want to be extra careful — a hash is enough for detection purposes.
- Keep using generic error messages (Section 5.2) to avoid account enumeration.
- OTP should still expire (keep existing expiry, e.g. 5–10 min) and still be single-use.
- `resetSessionToken` should also expire (e.g. 15–20 min total flow) so a stale Step-2-passed session can't be used to slow-walk an attack.

---

## 8. Edge Cases to Handle

| Case | Expected behavior |
|---|---|
| Existing user has no `recovery_email` set (pre-migration) | Forgot Password stops after Step 1 with a message directing them to set one from Account Settings while logged in, or contact support |
| User enters recovery email that matches a *different* account's recovery email | Still compare only against the account identified in Step 1 — irrelevant if it matches someone else's |
| User tries to skip to OTP page via direct URL/route | Blocked server-side by session stage check (Section 7.3); redirect to Step 2 |
| User submits recovery email same as registered email at signup | Blocked at signup with inline validation error (Section 4) |
| Too many wrong recovery email attempts | Lock that reset session temporarily, show generic rate-limit message |
| OTP step reached but recovery email step was somehow bypassed | Should be impossible given 7.3, but add a server-side assertion/log-alert if OTP verify is ever called without `recovery_verified` stage — treat as a security event |

---

## 9. Testing Checklist

- [ ] New signups cannot submit without a recovery email
- [ ] Recovery email = account email is rejected at signup
- [ ] Forgot Password: wrong recovery email → generic error, no OTP sent
- [ ] Forgot Password: correct recovery email → OTP sent to *registered* email (not recovery email)
- [ ] OTP page visuals/animations unchanged (pixel/behavior diff against current build)
- [ ] New Password page visuals/animations unchanged
- [ ] Password requirement rules still enforced both client- and server-side
- [ ] Cannot call OTP-verify or update-password endpoints directly, skipping recovery-email step
- [ ] Rate limiting triggers correctly on repeated wrong recovery email guesses
- [ ] Existing users without recovery email get a clear, non-broken path (Section 8)
- [ ] Copy on recovery email page updated exactly as specified in Section 5.2

---

## 10. Copy Changes Summary (for quick reference)

**File/page:** Forgot Password → Recovery Email step

**Replace:**
> Enter your registered email address below. We'll verify your registered account and send a 6-digit OTP code to reset your password.

**With:**
> Enter your recovery email address below. We'll verify your registered account and send a 6-digit OTP code to reset your password.

No other copy changes required — OTP and New Password pages keep their existing text as-is, including the password requirements block already in production.
