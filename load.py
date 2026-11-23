"""Load TSV exports of the pharmacy network into the SQLite warehouse."""
import argparse
import csv
import sqlite3
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent / "02 Исходные данные" / "Аптечная сеть"

def rows(source, filename, columns):
    with (source / filename).open(encoding="cp1251", newline="") as stream:
        reader = csv.reader(stream, delimiter="\t")
        if next(reader, None) != list(columns):
            raise ValueError(f"{filename}: unexpected header")
        for line, row in enumerate(reader, 2):
            if not row:
                continue
            if len(row) != len(columns) or any(not value.strip() for value in row):
                raise ValueError(f"{filename}:{line}: invalid or empty field")
            yield row

def unique(records, filename):
    result = {}
    for row in records:
        if row[0] in result:
            raise ValueError(f"{filename}: duplicate code {row[0]}")
        result[row[0]] = row
    return list(result.values())

def load(source, target, replace_days):
    groups = unique(
        ((int(code), name) for code, name in rows(source, "groups.txt",
          ("Группа.Код", "Группа.Наименование"))), "groups.txt")
    products = unique(
        ((int(code), name, int(group)) for code, name, group in rows(source, "produces.txt",
          ("Товар.Код", "Товар.Наименование", "Группа.Код"))), "produces.txt")
    stores = unique(
        ((int(code), name) for code, name in rows(source, "stores.txt",
          ("Отдел.Код", "Отдел.Наименование"))), "stores.txt")
    facts = defaultdict(lambda: [0, 0])
    dates = {}
    hours = set()
    sale_rows = 0
    for date, store, product, hour, quantity, amount in rows(source, "sales.txt",
            ("Дата", "Отдел.Код", "Товар.Код", "Час", "Количество", "Сумма")):
        day = datetime.strptime(date.split()[0], "%d.%m.%Y").date()
        iso = day.isoformat()
        hour = int(hour)
        cents = Decimal(amount.replace(",", ".")) * 100
        if not cents.is_finite() or cents != cents.to_integral_value():
            raise ValueError(f"Invalid monetary amount: {amount}")
        measures = facts[iso, int(store), int(product), hour]
        measures[0] += int(quantity)
        measures[1] += int(cents)
        dates[iso] = (iso, day.year, day.month)
        hours.add(hour)
        sale_rows += 1

    db = sqlite3.connect(target)
    try:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))
        with db:
            db.executemany("""INSERT INTO product_group VALUES (?, ?)
                              ON CONFLICT(group_id) DO UPDATE SET name=excluded.name""", groups)
            db.executemany("""INSERT INTO product VALUES (?, ?, ?)
                              ON CONFLICT(product_id) DO UPDATE
                              SET name=excluded.name, group_id=excluded.group_id""", products)
            db.executemany("""INSERT INTO store VALUES (?, ?)
                              ON CONFLICT(store_id) DO UPDATE SET name=excluded.name""", stores)
            db.executemany("INSERT OR IGNORE INTO calendar_day VALUES (?, ?, ?)", dates.values())
            db.executemany("INSERT OR IGNORE INTO purchase_hour VALUES (?)", [(h,) for h in hours])
            if replace_days:
                db.executemany("DELETE FROM sale WHERE sale_date = ?", [(day,) for day in dates])
            db.executemany("""INSERT INTO sale VALUES (?, ?, ?, ?, ?, ?)
                              ON CONFLICT(sale_date, store_id, product_id, hour) DO UPDATE
                              SET quantity=excluded.quantity, amount_cents=excluded.amount_cents""",
                           (key + tuple(measures) for key, measures in facts.items()))
            if db.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Broken references in the warehouse")
        count, quantity, cents = db.execute(
            "SELECT count(*), sum(quantity), sum(amount_cents) FROM sale").fetchone()
        print(f"Input sales rows: {sale_rows}; distinct input keys: {len(facts)}")
        print(f"Warehouse rows: {count}; quantity: {quantity or 0}; "
              f"amount: {Decimal(cents or 0) / 100:.2f}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--db", type=Path, default=HERE / "pharma.sqlite")
    parser.add_argument("--replace-days", action="store_true",
                        help="Replace all sales for dates in a complete daily extract")
    args = parser.parse_args()
    load(args.source, args.db, args.replace_days)
