# AI_USAGE.md — AI Collaboration Log


## How I Used It

I used AI as a coding collaborator, not a code generator. My workflow was:

1. I'd identify the problem or feature I needed
2. Describe the requirement to the AI
3. Review what it produced, test it, and modify where needed
4. Push once I was satisfied it was correct

The AI wrote first drafts of models, serializers, and views. I reviewed every file before committing. The anomaly detector logic, balance engine algorithm, and import wizard flow were all things I iterated on heavily.

---

## Key Prompts

- *"Build a CSV parser that flags anomalies across 8 categories — dates, names, amounts, duplicates, memberships, semantics, math, and currency. Don't silently fix things, surface each issue to the user."*
- *"The balance engine needs to handle temporal membership — Meera left in March, Sam joined in April. Make sure split calculations exclude members who weren't active on the expense date."*
- *"Use a greedy algorithm to minimize the number of settlement transactions from a dict of net balances."*
- *"Configure Django for production on Render with WhiteNoise for static files and dj-database-url for the database connection string."*

---

## Three Cases Where AI Got It Wrong

### Case 1 — Tailwind v4 CSS import order bug

The AI initially installed Tailwind CSS v4 (the newest version) for the frontend. When deployed to Vercel, the layout completely broke — the Navbar was overlapping content, cards had no spacing, and the background color vanished. Locally it looked fine.

**What I noticed:** The live Vercel build looked completely different from the local dev server. Something about the production build was stripping the layout classes.

**What was wrong:** In Tailwind v4, the `@import "tailwindcss"` directive must come *after* any `@import url()` statements. The AI had them in the wrong order. In development the browser tolerates this; in Vite's production build it doesn't.

**What I changed:** I ended up downgrading to Tailwind v3 (the stable version) entirely, creating a proper `tailwind.config.js` and `postcss.config.js`, and replacing the `@import "tailwindcss"` with the standard `@tailwind base; @tailwind components; @tailwind utilities;` directives. This is the version that actually works reliably in both dev and production.

---

### Case 2 — Axios interceptor using hardcoded `/api` URL on token refresh

The AI wrote the JWT auto-refresh interceptor in `axios.js` like this:

```js
const res = await axios.post('/api/auth/refresh/', { refresh: tokens.refresh });
```

**What I noticed:** In production, the Vercel-deployed frontend uses an absolute backend URL (Render's domain), not a relative `/api` path. The refresh interceptor was using the raw `axios` import with a hardcoded relative path instead of the configured `api` instance.

**What was wrong:** This meant that when a token expired in production, the refresh call would hit the wrong URL (a 404 on Vercel instead of Render), and the user would get silently logged out.

**What I changed:** Replaced `axios.post('/api/auth/refresh/', ...)` with `api.post('/auth/refresh/', ...)` so the refresh call always goes through the same configured Axios instance with the correct base URL.

---

### Case 3 — CSS variables lost during Tailwind downgrade

When I asked the AI to downgrade from Tailwind v4 to v3, it correctly updated the `@tailwind` directives but forgot to move the CSS custom properties (the `--color-bg`, `--color-surface`, etc.) from the old Tailwind v4 `@theme {}` block to a standard CSS `:root {}` block.

**What I noticed:** After the downgrade, the background was suddenly white. The dark navy theme had completely disappeared. The text was white-on-white — you could only see it if you highlighted it.

**What was wrong:** In Tailwind v4, CSS variables are declared inside `@theme {}`. When we switched to v3, that block got removed but the variables were never moved to a `:root {}` block, so the entire color system was broken.

**What I changed:** Added a proper `:root { --color-bg: #0f0d2e; ... }` block back into `index.css` with all the color and font variables. Pushed the fix and Vercel redeployed correctly.

---

## Bottom Line

The AI was genuinely useful for generating boilerplate and structure, but I had to stay alert, especially around deployment edge cases and anything that behaves differently between dev and production. Every bug above only showed up in production, which is exactly why you can't just ship what the AI produces without testing it end-to-end.
