# Workday ELT Pipeline — Mock API → Airflow → Snowflake → dbt

## Overview

A fully self-contained ELT pipeline simulating a real Workday integration. A FastAPI mock service generates realistic HR data with hires, terminations, promotions, and transfers — enabling real incremental loads, SCD2 history tracking, and change detection.

```
┌──────────────────────────────────────── Docker ─────────────────────────────────────┐
│                                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐                │
│  │  Mock Workday    │     │  Airflow         │     │  Postgres       │                │
│  │  API (FastAPI)   │────▶│  (scheduler +    │     │  (AF metadata)  │                │
│  │  :8000           │     │   webserver)     │     │  :5432          │                │
│  │                  │     │  :8080           │     │                 │                │
│  │  /workers        │     │                  │     └─────────────────┘                │
│  │  /positions      │     │  extract → load  │                                       │
│  │  /organizations  │     │  → dbt refined   │                                       │
│  │  /compensation   │     │  → dbt curated   │──────────▶  Snowflake (external)      │
│  │  /time_off       │     │  → dbt test      │            ┌──────────────────┐       │
│  │  /job_changes    │     │                  │            │ RAW              │       │
│  │                  │     └─────────────────┘            │ REFINED          │       │
│  │  POST /simulate  │                                     │ CURATED          │       │
│  │  (generate       │                                     │  dim_worker SCD2 │       │
│  │   changes)       │                                     │  dim_org         │       │
│  └─────────────────┘                                     │  fct_headcount   │       │
│                                                           │  fct_compensation│       │
└──────────────────────────────────────────────────────────┘  fct_turnover     │       │
                                                            └──────────────────┘       │
```

## What Makes This Interesting

| Challenge | How this project solves it |
|-----------|--------------------------|
| Incremental loads | `updated_since` filter — only pull changed records |
| SCD2 history | `dim_worker` tracks hires, promotions, transfers, terminations |
| Nested JSON flattening | Workday-style nested objects in the refined layer |
| Late-arriving changes | Backdated job changes and compensation adjustments |
| Pagination | Offset/limit with total count, just like real Workday |
| Idempotent loads | COPY INTO with file tracking, dedup in dbt |
| Change simulation | POST /simulate generates realistic workforce events |

## Quick Start

### 1. Snowflake Setup

```sql
USE ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS WORKDAY_WH
  WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;

CREATE DATABASE IF NOT EXISTS WORKDAY_DB;
CREATE SCHEMA IF NOT EXISTS WORKDAY_DB.RAW;
CREATE SCHEMA IF NOT EXISTS WORKDAY_DB.REFINED;
CREATE SCHEMA IF NOT EXISTS WORKDAY_DB.CURATED;

CREATE ROLE IF NOT EXISTS WORKDAY_ROLE;
GRANT USAGE ON WAREHOUSE WORKDAY_WH TO ROLE WORKDAY_ROLE;
GRANT ALL ON DATABASE WORKDAY_DB TO ROLE WORKDAY_ROLE;
GRANT ALL ON ALL SCHEMAS IN DATABASE WORKDAY_DB TO ROLE WORKDAY_ROLE;
GRANT ALL ON FUTURE TABLES IN DATABASE WORKDAY_DB TO ROLE WORKDAY_ROLE;
GRANT ALL ON FUTURE VIEWS IN DATABASE WORKDAY_DB TO ROLE WORKDAY_ROLE;
GRANT ROLE WORKDAY_ROLE TO USER <your_username>;
```

### 2. Configure

```bash
cp .env.example .env
# Fill in your Snowflake credentials
```

### 3. Run

```bash
docker compose up -d
```

- **Airflow UI**: http://localhost:8080 (admin / admin)
- **Mock Workday API**: http://localhost:8000/docs (Swagger UI)
- **Simulate changes**: `curl -X POST http://localhost:8000/simulate`

### 4. Trigger Pipeline

In Airflow UI → enable and trigger `workday_to_snowflake` DAG.

## API Endpoints

| Endpoint | Description | Params |
|----------|-------------|--------|
| GET /workers | Employee records with nested job/org | `updated_since`, `offset`, `limit` |
| GET /positions | Position catalog | `updated_since`, `offset`, `limit` |
| GET /organizations | Org hierarchy | `updated_since`, `offset`, `limit` |
| GET /compensation | Salary and bonus records | `updated_since`, `offset`, `limit` |
| GET /time_off | PTO/leave records | `updated_since`, `offset`, `limit` |
| GET /job_changes | Promotions, transfers, terms | `updated_since`, `offset`, `limit` |
| POST /simulate | Generate random workforce changes | `num_events` (default 10) |
| GET /health | Health check | - |

## Project Structure

```
workday-elt-pipeline/
├── docker-compose.yml
├── .env.example
├── mock-api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                    # FastAPI app with all endpoints
│   └── data_generator.py         # Faker-based workforce simulator
├── airflow/
│   ├── Dockerfile
│   ├── dags/
│   │   └── workday_to_snowflake.py
│   └── include/
│       └── extract/
│           └── workday_client.py # Paginated API client
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── refined/              # Flatten, type, dedupe
│       │   ├── stg_workers.sql
│       │   ├── stg_job_changes.sql
│       │   ├── stg_compensation.sql
│       │   └── schema.yml
│       └── curated/              # SCD2 dims, facts, metrics
│           ├── dim_worker.sql    # SCD2 with effective dates
│           ├── dim_org.sql
│           ├── fct_headcount_daily.sql
│           ├── fct_compensation.sql
│           └── schema.yml
└── data/landing/
```
