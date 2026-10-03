# Manual Functional Test Checklist

Run these checks against a local database containing sample data. Use separate
Staff, Manager, and Admin sessions where noted.

## Authentication and authorization

- [ ] Logged out, opening `/`, `/food`, `/inventory`, `/missions`,
      `/astronauts`, `/allocations`, or `/transactions` redirects to `/login`.
- [ ] A valid account can log in; a wrong email/password gets a generic error.
- [ ] Logout clears the session, and protected routes require signing in again.
- [ ] Staff can view pages, record a stock transaction, and create an allocation.
- [ ] Staff cannot access manager/admin edit or delete endpoints directly; the
      request returns 403.
- [ ] A Manager can manage missions, astronauts, food, inventory, and
      allocations but cannot delete a food item.
- [ ] An Admin can perform the Admin-only food deletion when no references
      block it.

## Dashboard and page controls

- [ ] Dashboard totals, recent five transactions, and items expiring in the
      next 30 days match the database.
- [ ] Food search, category, and supplier filters can be combined.
- [ ] Inventory search and stock/expiry status filters show the expected rows;
      expired and expiring-soon summary counts are correct.
- [ ] Mission status and type filters can be combined with mission search.
- [ ] Astronaut search and mission filter can be combined.
- [ ] Allocation search, mission filter, and food filter can be combined.
- [ ] Transaction food search and type filter work; the OUT summary includes
      both OUT and WASTAGE quantities.
- [ ] Empty tables and lists show their empty-state message.
- [ ] At mobile width, navigation, summary cards, filters, and tables remain
      usable without the desktop layout breaking.

## Stock and relationship integrity

- [ ] A positive `IN` transaction increases stock; `RETURN` also increases it.
- [ ] `OUT` and `WASTAGE` decrease stock; trying to remove more than available
      stock is rejected without inserting a transaction.
- [ ] Zero, negative, non-numeric, and excessively large quantities are
      rejected on applicable forms.
- [ ] A valid allocation decreases stock by its quantity.
- [ ] An allocation with insufficient stock is rejected and is not inserted.
- [ ] Selecting a mission limits the astronaut choices to that mission; the
      server also rejects an astronaut from another mission.
- [ ] Editing an allocation deducts/returns only the quantity difference.
- [ ] Changing an allocation's food item returns the old food and deducts the
      new food atomically.
- [ ] Deleting an allocation restores its food quantity.
- [ ] Deleting a referenced astronaut, mission, or food item is blocked with
      the related-record counts; after dependencies are removed, deletion can
      proceed for an authorized role.

## Schema upgrade

- [ ] Back up the database before running `database/migrate_schema.py`.
- [ ] Run the schema migration twice; the second run reports existing indexes
      and constraints without duplicating them.
- [ ] If legacy rows violate a CHECK constraint, the migration identifies the
      constraint and offending row count before applying additions.
