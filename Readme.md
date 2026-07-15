# Poultry Farm Record System

A computerised record system for a **single poultry farm** running **both layers
and broilers**. It replaces manual paper record-keeping with digital capture of
flock inventory, feed, health, production, and finances, and surfaces the data as
dashboards and reports for decision-making.

Built as a server-rendered Django application (no SPA, no REST API).

---

## Features

- **Accounts & roles** — three roles with enforced permissions:
  - **Owner/Admin** — everything, including user management and reference data.
  - **Manager** — full data entry, finance, and reports.
  - **Attendant** — create/view daily records only (mortality, feed, health, production).
- **Flock / batch inventory** — register batches; auto-computed current bird
  count, age, and mortality rate; per-flock detail page aggregating every module.
- **Feed** — purchases and consumption, live stock levels with low-stock alerts.
- **Health** — vaccination / medication / treatment records and a vaccination
  schedule with due/overdue tracking per batch.
- **Production** — egg collection (hen-day %) for layers, sample weights for
  broilers, and Feed Conversion Ratio; per-batch trend charts.
- **Finance** — income/expense transactions with per-batch and farm-wide
  profit & loss and cost-per-bird. Feed purchases and costed health records post
  expenses automatically (read-only in finance — no double entry).
- **Dashboard** — KPI cards, production/mortality trend charts, expense
  breakdown, and an alerts panel.
- **Reports & export** — batch performance, mortality, feed, production, and
  financial reports with date-range filters; export to **Excel** and **PDF**,
  plus printable views.
- **Validation throughout** — no future-dated daily records, no negative amounts,
  and quantities can't exceed available birds/stock.

## Tech stack

- **Django 5.2 LTS** (Python 3.12), server-rendered templates
- **SQLite** (default; PostgreSQL is the intended production target)
- **Tailwind CSS** (Play CDN in dev), **Alpine.js**, **Chart.js**
- **openpyxl** (Excel export), **xhtml2pdf** (PDF export)
- **python-decouple** for environment-based configuration

---

## Getting started

### Prerequisites
- Python 3.12+
- A virtual environment (the repo assumes one at the sibling folder
  `../poultry_farm`, but any venv works).

### Setup

```bash
# 1. Create & activate a virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (optional — sensible defaults exist)
#    Copy .env.example to .env and adjust as needed.
cp .env.example .env

# 4. Apply migrations
python manage.py migrate

# 5. Create an admin user, then set its role to OWNER in /admin/
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in.

### Environment variables

Read from `.env` via `python-decouple` (all optional — defaults shown):

| Variable          | Default                        | Purpose                                  |
|-------------------|--------------------------------|------------------------------------------|
| `SECRET_KEY`      | insecure dev key               | Django secret key (set a real one in prod). |
| `DEBUG`           | `True`                         | Debug mode. Set `False` in production.   |
| `ALLOWED_HOSTS`   | empty                          | Comma-separated allowed hosts.           |
| `CURRENCY_SYMBOL` | `₦`                            | Symbol used to format money in the UI.   |

---

## Demo data

Load a full demo farm (two batches with a few weeks of records) in one command:

```bash
python manage.py seed_demo            # load demo data (skips if already present)
python manage.py seed_demo --fresh    # wipe demo data and reload
```

This creates three users — `demo_owner`, `demo_manager`, `demo_attendant`
(password `demo1234!`) — plus reference data, a layer batch and a broiler batch
with mortality, feed, health, production, and sales records.

## Running the tests

```bash
python manage.py test
```

The suite has **108 tests** covering derived calculations (current quantity,
age, mortality rate, hen-day %, FCR, stock levels, P&L, cost-per-bird),
input validation, and role-based permissions.

---

## Project structure

```
poultry_record_system/
├── accounts/     # Custom user model, roles, login, user management
├── core/         # BaseModel (audit trail), reference data, role mixins, seed_demo
├── inventory/    # Batch & mortality records, batch detail page
├── feed/         # Feed purchases & consumption, stock levels
├── health/       # Health records & vaccination schedule
├── production/   # Egg production & weight records, FCR
├── finance/      # Transactions, profit & loss
├── dashboard/    # KPI dashboard, alerts, charts
├── reports/      # Reports + Excel/PDF export
├── templates/    # base.html, shared partials
└── poultry_record_system/   # Project settings & root URLs
```

Every domain model inherits an abstract `BaseModel` providing a
`created_by` / `updated_by` / `created_at` / `updated_at` audit trail.

## Notes

- **Money & counts:** money and weights use `DecimalField`; bird counts and eggs
  use `PositiveIntegerField`.
- **Tailwind** is loaded via the Play CDN for development; for production, build a
  compiled stylesheet with the standalone Tailwind CLI.
- **PDF export** uses xhtml2pdf (pure-Python, no system libraries required).
