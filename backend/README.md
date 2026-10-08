# Backend: Pantry Sign-In API

FastAPI + PostgreSQL. It stores check-ins sent by the frontend, works out how many
unique households they represent, and serves the counts for the dashboard.

## Setup (once)

Needs Python 3.11 or newer and PostgreSQL.

**1. PostgreSQL and two databases** (one for development, one the tests wipe):

```sh
brew install postgresql@18
brew services start postgresql@18
createdb mock_hackathon
createdb mock_hackathon_test
```

On Windows, install PostgreSQL from postgresql.org and create the same two databases.

**2. Python packages:**

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Settings:** copy `.env.example` to `.env`, then fill in `PHONE_HMAC_KEY` with the output of:

```sh
python -c "import secrets; print(secrets.token_hex(32))"
```

If your Postgres needs a user and password (the Windows installer sets one), also change
`DATABASE_URL` to `postgresql+psycopg://postgres:YOUR_PASSWORD@localhost/mock_hackathon`.

**4. Tables:**

```sh
alembic upgrade head
```

This also adds two demo pantries, `loc-1` and `loc-2`.

## Run, test, demo

```sh
fastapi dev app/main.py        # http://localhost:8000/docs to try every endpoint
pytest                         # uses mock_hackathon_test, never your dev data
python -m scripts.demo_seed    # with the server running: sync, retry, dedup, counts
```

To point the frontend at it, put `VITE_API_URL=http://localhost:8000` and
`VITE_USE_MOCKS=false` in `frontend/.env.local`.

## Endpoints

| Endpoint | What it does |
|---|---|
| `GET /api/health` | `{"status": "ok"}` when the API and database are up. Never needs a token. |
| `GET /api/locations` | Active pantries: `id`, `name`, `address`. |
| `POST /api/sync` | Stores a batch of visits (up to 500). Safe to retry. |
| `POST /api/dedup/run` | Groups visits into households and reports what it did. |
| `GET /api/reviews` | Near matches waiting for a person to decide. |
| `GET /api/metrics` | `unique_households`, `total_visits`, `pending_review`, `anonymous_visits`, `unprocessed_visits`. |

If `API_TOKEN` is set in `.env`, everything except health needs `Authorization: Bearer <token>`
and answers 401 without it. Leave it empty for local development.

### Sending visits

Every visit has `id` (a UUID made on the device), `location_id` and `visited_at`
(device time, with a UTC offset). `method` decides which other fields go with it.
Send only those fields: anything extra gets the visit rejected.

```json
{"visits": [
  {"id": "...", "location_id": "loc-1", "visited_at": "2026-10-08T14:30:00Z",
   "method": "phone", "phone": "(555) 123-4567", "household_size": 4},

  {"id": "...", "location_id": "loc-1", "visited_at": "2026-10-08T14:35:00Z",
   "method": "no_phone", "first_initial": "M", "birth_month": 3, "birth_year": 1988, "household_size": 2},

  {"id": "...", "location_id": "loc-1", "visited_at": "2026-10-08T14:40:00Z",
   "method": "anonymous"}
]}
```

`household_size` is optional for `phone` and required for `no_phone`. Any visit may add
`"language": "en"` or `"es"`.

The response has one result per visit, in the same order:

```json
{"results": [
  {"id": "...", "status": "created", "error": null},
  {"id": "...", "status": "duplicate", "error": null},
  {"id": "...", "status": "rejected", "error": "birth_month: Input should be less than or equal to 12"}
]}
```

- `created` and `duplicate` both mean the server has the visit, so it can leave the offline queue.
- `rejected` means that visit will never be accepted as it is. The rest of the batch is still stored.
- A 422 for the whole request only happens when the body is malformed or a visit has no valid `id`.

### How dedup decides

Phone visits with the same number are one household, across all pantries.

A no-phone visit is scored against the no-phone households already known:

| Detail | Points |
|---|---|
| First initial matches | 0.35 |
| Birth year matches | 0.30 |
| Birth month matches | 0.20 |
| Household size the same (off by one: 0.075) | 0.15 |

| Score | Result |
|---|---|
| 0.90 or more | Joins that household. |
| 0.70 to 0.89, or a tie between two households | Goes to the review list and has no household yet. |
| Below 0.70 | Becomes a new household. |

The two thresholds are `DEDUP_MERGE_THRESHOLD` and `DEDUP_REVIEW_THRESHOLD` in `.env`.
Anonymous visits count as visits but are never given a household.

The job only fills in `visits.household_id`. It never deletes or rewrites a visit, and
running it again when nothing is new changes nothing.

## Privacy rules

- A raw phone number is never stored. The server turns it into an HMAC-SHA256 hash with
  `PHONE_HMAC_KEY` and keeps only that. The `visits` table has no column that could hold the number.
- Never change `PHONE_HMAC_KEY` once real data exists: the same phone would hash differently
  and returning visitors would stop matching.
- No name or email fields, ever. The visit models refuse unknown fields.
- Error messages say which rule was broken, never the value that was sent.

## When you change something

- **An endpoint or a request/response shape:** run `python -m scripts.export_openapi` and commit
  the updated `openapi.json` at the repo root. A test fails until you do. The frontend then
  runs `npm run gen:api`.
- **A table:** edit `app/models.py`, run `alembic revision --autogenerate -m "what changed"`,
  read the new file in `alembic/versions/`, then `alembic upgrade head`.

## Troubleshooting

- **"connection refused"**: Postgres is not running. `brew services start postgresql@18`.
- **An error naming `phone_hmac_key` at startup**: there is no `.env`, or `PHONE_HMAC_KEY` in it is empty or shorter than 32 characters.
- **Start over with an empty database**: `alembic downgrade base && alembic upgrade head`.
