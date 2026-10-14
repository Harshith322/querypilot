# QueryPilot

A Text-to-SQL analytics agent. Ask a business question in plain English, get validated read-only SQL, the result, computed insights and a chart.

Built on PostgreSQL with the Olist Brazilian e-commerce dataset (Kaggle). Python, FastAPI, sqlglot, Claude, pandas, matplotlib.

## How it works

```
question
   |
   v
schema text (tables, keys, allowed values) + question  ->  Claude  ->  SQL
   |
   v
sqlglot validator: one SELECT only, table allowlist, LIMIT enforced, SQL rewritten
   |  rejected -> error sent back to Claude, retry (max 2 retries)
   v
execute on read-only role, read-only transaction, statement timeout
   |  database error -> error sent back to Claude, retry
   v
analysis: result profile, deterministic chart choice, insights computed from the data
   |
   v
JSON response and web UI: SQL, insights, chart, result table, attempts
```

## Safety design

1. Validation: only a single SELECT or UNION is accepted. INSERT, UPDATE, DELETE, DDL, SELECT INTO, FOR UPDATE, multiple statements, system catalogs, schema-qualified tables and dangerous functions (pg_*, dblink, set_config and others) are rejected.
2. The validator rewrites the query and the rewritten SQL is what runs, so comments cannot smuggle anything through. A LIMIT is added or capped to 1000 rows.
3. Execution uses a Postgres role with SELECT only, inside a read-only transaction, with a 5 second statement timeout. A bug in the validator still cannot write data.
4. Insights and chart choice are computed in code from the result, not written by the model, so reported numbers cannot be hallucinated.

## Requirements

Python 3.11 or newer, Docker, an Anthropic API key.

## Setup

```bash
git clone https://github.com/Harshith322/querypilot.git
cd querypilot

python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env               # then edit .env and set ANTHROPIC_API_KEY
set -a; source .env; set +a        # Windows PowerShell: set each variable with $env:NAME="value"

docker compose up -d               # starts PostgreSQL 16
```

Check the repo URL above matches your actual GitHub repository name.

## Load data

Option A, quick start with synthetic Olist-shaped sample data (300 orders):

```bash
python -m scripts.init_db --sample
```

Option B, the real dataset:

1. Download the Brazilian E-Commerce Public Dataset by Olist from Kaggle and unzip it into `data/olist/`.
2. Load it:

```bash
python -m scripts.init_db --csv-dir data/olist
```

Both options create the tables, add foreign keys, and create the `qp_readonly` role. The password in `db/roles.sql` is for local development only.

## Run

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000 and ask a question, for example:

1. Which product categories had the highest revenue?
2. How did monthly orders change over time?
3. What is the average review score by customer state?

Or call the API:

```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Top 5 product categories by revenue"}'
```

Other endpoints: `GET /health`, `GET /charts/{filename}`.

## Run the tests

Unit tests need nothing else:

```bash
python -m pytest -q
```

Database tests need a throwaway Postgres database. They are skipped unless these variables are set:

```bash
docker compose exec db psql -U postgres -c "CREATE DATABASE querypilot_test"
export QP_TEST_ADMIN_DSN=postgresql://postgres:postgres@localhost:5432/querypilot_test
export QP_TEST_READONLY_DSN=postgresql://qp_readonly:readonly@localhost:5432/querypilot_test
python -m pytest -q
```

The database tests recreate the tables in that database, so never point them at data you care about.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| ANTHROPIC_API_KEY | none | Anthropic API key |
| QP_MODEL | claude-sonnet-5-5 | Model used for SQL generation |
| QP_ADMIN_DSN | postgresql://postgres:postgres@localhost:5432/querypilot | Used only by the init scripts |
| QP_READONLY_DSN | postgresql://qp_readonly:readonly@localhost:5432/querypilot | Used by the app |
| QP_MAX_ROWS | 1000 | Row cap enforced by the validator |
| QP_STATEMENT_TIMEOUT_MS | 5000 | Query timeout |

## Project layout

```
app/
  config.py        settings from environment
  db.py            read-only query execution
  schema.py        schema introspection for the prompt
  validator.py     sqlglot safety validation and rewrite
  prompts.py       system prompt and dataset notes (edit for other datasets)
  llm.py           LLM interface and Anthropic client
  sqlgen.py        prompt building and SQL extraction
  analysis/        result profile, chart choice, insights
  agent/           orchestrator with retry loop, tool spec, wiring
  main.py          FastAPI app
  static/          web UI
db/                schema, constraints, read-only role
scripts/           database init, CSV loader, sample data
tests/             unit and database tests
```

## Using another dataset

1. Replace `db/schema.sql` and `db/constraints.sql` with your tables.
2. Update `DOMAIN_NOTES` in `app/prompts.py` with business definitions such as what counts as revenue.
3. Load your data and rerun `python -m scripts.init_db`, adjusting the loader for your files.

## Limitations

1. Single-turn: each question is answered independently, with no conversation memory.
2. Accuracy depends on the model and on the schema and notes in the prompt. No accuracy number is reported yet, because the evaluation set has not been run.
3. The validator checks tables, not columns. Unknown columns are caught by the database and fed back to the model.
4. Chart choice is rule-based and covers line, bar, scatter and histogram only.
5. Charts are written to a local `charts/` folder with no cleanup.

## Evaluation

Not run yet. Planned: a set of questions with gold SQL, scored by comparing execution results, reporting execution accuracy, retry rate and latency. Add the measured numbers here only after running it.
