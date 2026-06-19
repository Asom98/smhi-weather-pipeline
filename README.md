# SMHI Weather Pipeline

A scheduled batch ETL pipeline that pulls live weather observations from the
[SMHI Open Data API](https://opendata.smhi.se) (Swedish Meteorological
and Hydrological Institute), transforms them into tidy rows, and loads them
idempotently into Postgres — running automatically every day with no server
to manage and no cost.

## Architecture

```
            ┌──────────────────────┐
            │  GitHub Actions cron │   (runs daily, free on public repos)
            └──────────┬───────────┘
                       │ triggers
                       ▼
   ┌────────────────────────────────────┐
   │  Python ETL (src/pipeline.py)      │
   │  extract → transform → load        │
   └──────────┬──────────────────┬──────┘
              │ pulls            │ writes
              ▼                  ▼
      SMHI Open Data        Neon Postgres
      (public API)          (free, serverless)
```

## Tech stack

| Concern | Tool | Why |
|---|---|---|
| Language | Python 3.13 | Standard for data engineering work, typed, readable |
| HTTP client | `httpx` | Clean timeout/retry-friendly API |
| Retries | `tenacity` | Declarative exponential backoff on transient (5xx/network) failures only — a 404 means the station/parameter combo doesn't exist and is never retried |
| Database | Neon (serverless Postgres) | Free tier, scales to zero, just a connection string — no server to manage, no billing risk |
| Scheduler | GitHub Actions (`cron`) | Free and unlimited on public repos; no infrastructure to provision or pay for |
| Containerization | Docker | Disposable local Postgres for development, separate from production Neon |
| Driver | `psycopg2-binary` | No native build tools required |

**Idempotent loads:** the `observations` table has a composite primary key
(`station_id, parameter_id, timestamp`). Every load is an
`INSERT ... ON CONFLICT ... DO UPDATE`, so re-running the pipeline over
overlapping data (which happens naturally — SMHI's `latest-day` window
overlaps between consecutive daily runs) never creates duplicate rows.

## Running it locally

```bash
# 1. Clone and enter the repo
git clone https://github.com/Asom98/smhi-weather-pipeline.git
cd smhi-weather-pipeline

# 2. Create a virtual environment and install dependencies
python -m venv .venv
.venv/Scripts/activate      # on Windows
pip install -r requirements.txt

# 3. Copy the env template and fill in DATABASE_URL
cp .env.example .env

# 4. Start a local Postgres (or point DATABASE_URL at Neon directly)
docker compose up -d

# 5. Run the pipeline
python -m src.pipeline

# 6. Run the tests
pytest tests/
```

## Screenshots

- **Successful GitHub Actions run**: <img width="2538" height="1121" alt="Screenshot 2026-06-19 152333" src="https://github.com/user-attachments/assets/02a9c4f9-38d4-4cec-9d50-13fbe401312e" />

- **Sample rows in the database**: <img width="2557" height="1149" alt="Screenshot 2026-06-19 152148" src="https://github.com/user-attachments/assets/ef8141fa-dfc5-4329-a3d1-ee765d0ce18a" />


## What I learned / design decisions

- **Why GitHub Actions over a rented server**: a daily batch job doesn't need
  an always-on machine. GitHub Actions provisions a fresh VM per run and
  destroys it afterward — free, zero maintenance, and there's no server to
  patch or pay for.
- **Why Neon over a self-hosted database**: scales to zero when idle, so a
  once-a-day pipeline costs nothing between runs, with no risk of a surprise
  bill since there's no paid tier to accidentally trigger.
- **Why upserts instead of plain inserts**: SMHI's API only exposes a
  rolling `latest-day` window, so consecutive daily runs always see
  overlapping timestamps. Without `ON CONFLICT ... DO UPDATE`, every run
  would duplicate the previous day's data.
- **Why only retry on 5xx, not 404**: an early version retried on *any* bad
  HTTP status, including 404s for station/parameter combinations that don't
  exist. That wasted ~7 seconds per missing combination retrying something
  that could never succeed — fixed by only retrying on server errors (5xx)
  and network/connection failures.
- **Secrets never touch the repo**: locally, `DATABASE_URL` lives in a
  gitignored `.env` file; in CI, it's a GitHub Secret injected as an
  environment variable at runtime and never written to logs.

## Project structure

```
.
├── src/
│   ├── extract.py       # pull from SMHI API, with retry-on-5xx
│   ├── transform.py      # raw JSON -> tidy rows (pure functions)
│   ├── db.py              # Postgres connection + schema setup
│   ├── load.py            # idempotent upsert into Postgres
│   └── pipeline.py       # orchestrates extract -> transform -> load
├── sql/schema.sql        # observations table definition
├── tests/                 # unit tests for the transform logic
├── .github/workflows/    # the scheduled GitHub Actions workflow
└── docker-compose.yml    # local Postgres for development
```

## Phase 2: Apache Airflow (local orchestration showcase)

Phase 1 (GitHub Actions) is the **deployed, always-running** version of this
pipeline. Phase 2 demonstrates real orchestration with Apache Airflow,
**run locally on a laptop** — zero cost, no hosting. The DAG
(`airflow/dags/weather_pipeline_dag.py`) imports and calls the exact same
`src/` functions as `pipeline.py`, split into three dependent tasks
(`extract → transform → load`) so the DAG graph is meaningful — no ETL logic
is duplicated between the two phases.

It runs on Airflow's `LocalExecutor` (scheduler + webserver + a Postgres
metadata DB) rather than the heavier `CeleryExecutor` quick-start default,
since a single-laptop demo doesn't need a distributed worker pool or Redis
broker.

**Run it:**

```bash
cd airflow
docker compose up airflow-init      # first time only: creates metadata DB + admin user
docker compose up -d airflow-webserver airflow-scheduler
```

Open http://localhost:8080 (login `airflow` / `airflow`), unpause
`weather_pipeline`, and trigger a run from the UI — or via the CLI:

```bash
docker compose exec airflow-scheduler airflow dags trigger weather_pipeline
```

<img width="2458" height="1265" alt="Screenshot 2026-06-19 155624" src="https://github.com/user-attachments/assets/125fbc5b-c326-45d1-ab41-2217407066c9" />


## Roadmap

- **Stretch**: join in Trafikverket traffic data to analyze weather/traffic
  correlation in Skåne; a lightweight dbt layer; a minimal dashboard.
