# DECISIONS.md — Decision Log

Every significant design choice, what alternatives I considered, and why I went the way I did.

---

## 1. Tech Stack — Django + React

**Options considered:**
- Full-stack Django with server-rendered templates
- FastAPI + React
- Django REST Framework + React

**Decision:** Django REST Framework + React (Vite)

Django gives you a proper ORM, migrations, auth, and admin panel out of the box. For a data-heavy project like this where the schema needed to be designed carefully, I didn't want to build all that from scratch. FastAPI is faster for pure APIs but I'd lose a lot of the scaffolding I needed quickly.

React on the frontend because the CSV import flow has multiple steps (upload → review anomalies → confirm) and managing that kind of multi-step state is much cleaner with a component-based approach than with Django templates.

---

## 2. Settlement Optimization — Greedy Algorithm

**Options considered:**
- Show every individual debt pair (O(n²) transactions)
- Minimum spanning tree approach
- Greedy simplification (net each person's balance first, then settle)

**Decision:** Greedy simplification

The goal (from Aisha's request) was "one number per person — who pays whom, how much." 

The greedy approach works in two steps: First compute everyone's net balance (total paid minus total owed). Then repeatedly match the person who owes the most with the person who is owed the most. This minimizes the number of transactions needed. For 6 people, this is nearly optimal and much simpler to implement and explain than a full graph-based approach.

---

## 3. Anomaly Resolution — User-in-the-loop

**Options considered:**
- Silent auto-fix everything
- Reject the whole file if any error is found
- Flag each issue and let the user decide before committing

**Decision:** User-in-the-loop

Silent fixes are dangerous — if I auto-decide that a name typo maps to "Priya" and I'm wrong, the expense is permanently misattributed. Rejecting the whole file is useless for a file that clearly has partial valid data.

The import wizard shows every detected issue with a severity (error, warning, info, auto-fixed) and a suggested resolution. The user reviews them, then confirms. Nothing is written to the database until after that confirmation step.

---

## 4. Currency — Fixed Rate vs. Live API

**Options considered:**
- Fetch live USD/INR rate from an external API (like ExchangeRate-API)
- Store a fixed rate in settings and document it clearly

**Decision:** Fixed rate (85.0 INR/USD)

Using a live API introduces a network dependency that could break during demos, requires an API key, and creates nondeterminism — the same import done today vs. tomorrow would produce different balances. For this dataset (historical trip expenses), what matters is consistency, not real-time accuracy. I set USD_INR = 85.0 in settings and document it clearly so everyone knows what rate was used.

---

## 5. Temporal Membership — Separate Table vs. Date Fields on User

**Options considered:**
- Add `joined_at` and `left_at` fields directly on the group membership record
- Use a separate audit log table
- A full event-sourcing approach

**Decision:** `GroupMembership` join table with `joined_at` and `left_at`

The core problem is that Meera left in March and Sam joined in April. If expenses are just tied to a group, there's no way to correctly compute who should be charged for what. The `GroupMembership` table lets us ask `was_member_on(date)` for any expense date, which is exactly what the balance engine does.

A full event-sourcing approach is overkill for six people. The join table is simple, queryable, and covers the requirement.

---

## 6. Deployment — Render + Vercel vs. Single VPS

**Options considered:**
- Spin up a DigitalOcean droplet and deploy everything manually
- Use Heroku
- Use Render (backend + DB) + Vercel (frontend)

**Decision:** Render + Vercel

Heroku removed its free tier. A VPS needs Nginx config, SSL cert setup, and manual deployment pipelines. Render gives PostgreSQL, auto-deploy from GitHub, and HTTPS out of the box. Vercel is the standard for React frontends — instant CDN, automatic redeploy on push, free tier.

Splitting backend and frontend onto separate platforms is fine here because they communicate over HTTPS, and it lets each scale independently.

---

## 7. JWT Auth vs. Session Auth

**Options considered:**
- Django's built-in session-based auth
- JWT with SimpleJWT library

**Decision:** JWT (SimpleJWT)

Since the frontend is a separate app running on a different domain (Vercel vs. Render), cookie-based sessions would run into cross-origin issues and SameSite restrictions. JWTs sent in Authorization headers sidestep this entirely. SimpleJWT integrates cleanly with DRF and the token refresh interceptor on the Axios client handles silent re-auth transparently.
