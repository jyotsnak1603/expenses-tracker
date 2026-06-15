# SCOPE.md — Anomaly Log and Database Schema

This document covers two things: the data problems we found in the CSV and what the app does about each one, and the full database schema.

---

## Part 1 — Anomaly Log

We identified problems across 8 categories. The importer surfaces all of these to the user before a single row is committed to the database.

### Category A — Date and Amount Format Issues

| # | Problem | Example | How We Handle It |
|---|---|---|---|
| A1 | Non-standard date format | `Mar-14` instead of `14-03-2026` | Auto-fixed: parse and convert to DD-MM-YYYY. Flag it so the user can verify. |
| A2 | Ambiguous date | `04-05-2026` could be April 5 or May 4 | Warn user and default to DD-MM interpretation (consistent with other rows) |
| A3 | Invalid date string | `32-01-2026` or `hello` | Error: row is rejected |
| A4 | Comma-formatted amount | `1,200` | Auto-fixed: strip comma and parse as number |
| A5 | Excessive decimal precision | `1200.1667` | Auto-fixed: round to 2 decimal places |

### Category B — Name and Identity Issues

| # | Problem | Example | How We Handle It |
|---|---|---|---|
| B1 | Lowercase payer name | `rohan` | Auto-fixed: convert to title case |
| B2 | Mixed-case variant | `AISHA` | Auto-fixed |
| B3 | Leading/trailing whitespace | `" Priya"` | Auto-fixed: strip |
| B4 | Name variant or abbreviation | `Priya S` | Warning: fuzzy matched to Priya, user confirms |
| B5 | Informal participant names | `Dev's friend Kabir` | Warning: non-member detected, user decides whether to include |

### Category C — Missing Data

| # | Problem | How We Handle It |
|---|---|---|
| C1 | Missing payer (paid_by) | Error: cannot import, user must fix CSV |
| C2 | Missing split_type | If description mentions "paid back" or "settlement", auto-classify as settlement. Otherwise error. |
| C3 | Missing currency | Auto-fixed: default to INR |

### Category D — Duplicate Detection

| # | Problem | How We Handle It |
|---|---|---|
| D1 | Exact duplicate | Same date, payer, amount, similar description → Warning, suggest deleting one |
| D3 | Conflicting duplicate | Same date and description but different amounts or payers → Warning, user chooses which to keep |

### Category E — Math and Validation

| # | Problem | How We Handle It |
|---|---|---|
| E1 | Percentage splits don't sum to 100% | Error: cannot proceed |
| E2 | Unequal split amounts don't match expense total | Warning: show the discrepancy |
| E3 | Equal split with redundant detail column | Auto-fixed: ignore the detail column |

### Category F — Semantic and Business Logic

| # | Problem | How We Handle It |
|---|---|---|
| F1 | Settlement logged as expense | Warning: detected via keywords like "paid back", "settlement". Ask user to reclassify. |
| F2 | Missing split_type on settlement row | Auto-fixed if description gives it away |
| F3 | Zero amount | Warning: may be a placeholder |
| F4 | Negative amount | Warning: treated as a refund/reversal |
| F5 | Refund participant mismatch | Info: ask user to verify participants match original expense |
| F6 | Self-reported issue in notes | Info: surface to user (e.g., notes say "counted twice") |

### Category G — Membership and Timeline

| # | Problem | How We Handle It |
|---|---|---|
| G1 | Meera included after she left (end of March) | Warning: she shouldn't be in April+ expenses |
| G2 | Dev included as regular flatmate | Info: Dev was a trip guest, not a permanent flatmate |
| G3 | Sam included before he joined (April 8) | Warning: Sam shouldn't appear in March expenses |

### Category H — Currency

| # | Problem | How We Handle It |
|---|---|---|
| H1 | Expense is in USD | Info: will be converted to INR at fixed rate of 85.0 INR/USD |

---

## Part 2 — Database Schema

### `auth_user` (Django built-in)
Used as-is. Stores username, email, hashed password.

---

### `groups_group`
```
id              INT          PK
name            VARCHAR(200)
description     TEXT
default_currency VARCHAR(3)  default 'INR'
created_by_id   FK → auth_user
created_at      DATETIME
updated_at      DATETIME
```

---

### `groups_groupmembership`
This is the key table for temporal membership. Every join and leave event is a separate record, so we can ask "was Sam a member on March 15?" without ambiguity.

```
id          INT      PK
group_id    FK → groups_group
user_id     FK → auth_user
joined_at   DATE
left_at     DATE     nullable
is_active   BOOLEAN
created_at  DATETIME

UNIQUE (group_id, user_id, joined_at)
```

---

### `expenses_expense`
```
id              INT          PK
group_id        FK → groups_group
description     VARCHAR(500)
paid_by_id      FK → auth_user
amount          DECIMAL(12,2)
currency        VARCHAR(3)   default 'INR'
split_type      VARCHAR(20)  [equal | unequal | percentage | share]
date            DATE
notes           TEXT
is_settlement   BOOLEAN      default False
imported_from   VARCHAR(100) (tracks CSV source)
import_row      INT          nullable
created_at      DATETIME
updated_at      DATETIME
```

---

### `expenses_expensesplit`
One row per person per expense — what they owe.

```
id          INT           PK
expense_id  FK → expenses_expense
user_id     FK → auth_user
amount      DECIMAL(12,2) (share in original currency)

UNIQUE (expense_id, user_id)
```

---

### `expenses_settlement`
Distinct from expenses. Records actual payments between members.

```
id          INT           PK
group_id    FK → groups_group
paid_by_id  FK → auth_user
paid_to_id  FK → auth_user
amount      DECIMAL(12,2)
currency    VARCHAR(3)
date        DATE
notes       TEXT
created_at  DATETIME
```

---

### `importer_importsession`
Tracks in-progress CSV import state (anomalies, resolutions, status).

```
id              INT      PK
user_id         FK → auth_user
status          VARCHAR(20)  [pending | reviewing | confirmed | failed]
raw_data        JSON     (parsed CSV rows)
anomalies       JSON     (list of issues detected)
resolutions     JSON     (user decisions)
filename        VARCHAR(255)
created_at      DATETIME
updated_at      DATETIME
```
