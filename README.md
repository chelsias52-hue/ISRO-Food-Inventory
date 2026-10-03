# ISRO Food Inventory

A Flask and MySQL learning project for tracking food inventory, suppliers,
missions, crew, food allocations, and stock movements. All mission and crew
records are fictional sample data; this project is not connected to NASA,
ISRO, or an operational supply system.

## Requirements

- Python 3.10 or newer
- MySQL Server 8.0.16 or newer (CHECK constraints are enforced starting with
  MySQL 8.0.16)

## Setup on Windows

1. Start MySQL Server and create/initialize the database.
2. In PowerShell, from this project folder:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   py -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

3. Edit `.env` with your MySQL username/password and set `FLASK_SECRET_KEY`
   to a unique random value of at least 32 characters. Generate one with:

   ```powershell
   py -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Do not commit `.env` or reuse a production secret in development.
4. In MySQL Workbench, execute `database/schema.sql` to create an empty
   database. To load the fictional sample records, execute
   `database/data.sql` after the schema.
5. Start the application:

   ```powershell
   py app.py
   ```

   Open <http://127.0.0.1:5000>. The application reads `.env` automatically.
   If the MySQL password or Flask secret is blank, running `app.py` directly
   asks for it without echoing the input. Debug mode is off unless
   `FLASK_DEBUG=1` is explicitly set.

## Existing database upgrades

- For an older database with existing inventory tables, back up the database
  and run `py database/migrate_schema.py`. It adds the query indexes and
  CHECK constraints if missing, and reports legacy rows that must be corrected
  before a constraint can be applied. Run it with `.env` configured.
- If your database contains legacy plaintext user passwords, run
  `py database/migrate_passwords.py` before using the updated application.
  This one-time migration hashes existing passwords in place. It skips
  passwords that already use Werkzeug `pbkdf2:` or `scrypt:` hashes.
- New installs should use `schema.sql`; do not run the schema migration
  against a new database that already has those indexes and checks.

## Demo login

The sample SQL seeds `admin@isrofood.com` with password `admin123`. The
credential is included only for local demonstration. Remove or replace all
sample accounts before deployment; there is no public registration flow.

## Roles

| Capability | Staff | Manager | Admin |
| --- | --- | --- | --- |
| View dashboard and modules | Yes | Yes | Yes |
| Create stock transactions and food allocations | Yes | Yes | Yes |
| Add/edit food, inventory, missions, astronauts, allocations | No | Yes | Yes |
| Delete missions, astronauts, allocations | No | Yes | Yes |
| Delete food items | No | No | Yes |

Authorization is enforced by the server-side route decorators; hiding buttons
in templates is only a presentation detail.

## Inventory behavior

- `IN` and `RETURN` stock transactions add inventory.
- `OUT` and `WASTAGE` transactions subtract inventory.
- Creating, editing, or deleting an allocation deducts/returns stock in the
  same database transaction as the allocation change.
- Allocation edits and deletions lock affected inventory rows before changing
  stock. Insufficient stock and quantity overflow are rejected.
- Food, mission, and astronaut deletion is blocked while dependent records
  remain. No foreign keys use cascading deletes.

The schema includes foreign keys, positive/nonnegative quantity checks, and
indexes for expiry, mission status/launch date, allocation date, and recent
stock transactions. MySQL automatically indexes foreign-key columns where
needed.

## Manual verification

See [MANUAL_TEST_CHECKLIST.md](./MANUAL_TEST_CHECKLIST.md) for login,
authorization, filtering, stock, relationship, and responsive-layout checks.

## Configuration reference

| Variable | Purpose |
| --- | --- |
| `MYSQL_HOST` | MySQL server hostname (default `localhost`) |
| `MYSQL_USER` | MySQL account (default `root`) |
| `MYSQL_PASSWORD` | MySQL password |
| `MYSQL_DATABASE` | Database name (default `nasa_food_inventory`) |
| `FLASK_SECRET_KEY` | Flask session-signing secret (or `SECRET_KEY`) |
| `FLASK_COOKIE_SECURE` | Set to `1` only when served over HTTPS |
| `FLASK_DEBUG` | Set to `1` for local development only |
