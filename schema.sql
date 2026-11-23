CREATE TABLE IF NOT EXISTS product_group (
    group_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
) STRICT;

CREATE TABLE IF NOT EXISTS product (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    group_id INTEGER NOT NULL REFERENCES product_group(group_id)
) STRICT;

CREATE TABLE IF NOT EXISTS store (
    store_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
) STRICT;

CREATE TABLE IF NOT EXISTS calendar_day (
    sale_date TEXT PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12)
) STRICT;

CREATE TABLE IF NOT EXISTS purchase_hour (
    hour INTEGER PRIMARY KEY CHECK (hour BETWEEN 0 AND 23)
) STRICT;

CREATE TABLE IF NOT EXISTS sale (
    sale_date TEXT NOT NULL REFERENCES calendar_day(sale_date),
    store_id INTEGER NOT NULL REFERENCES store(store_id),
    product_id INTEGER NOT NULL REFERENCES product(product_id),
    hour INTEGER NOT NULL REFERENCES purchase_hour(hour),
    quantity INTEGER NOT NULL,
    amount_cents INTEGER NOT NULL,
    PRIMARY KEY (sale_date, store_id, product_id, hour)
) STRICT;

CREATE VIEW IF NOT EXISTS sales_for_cube AS
SELECT s.sale_date, d.year, d.month, substr(s.sale_date, 1, 7) AS year_month,
       a.name AS store_name, g.name AS group_name, p.name AS product_name,
       s.hour, s.quantity, s.amount_cents, s.amount_cents / 100.0 AS amount
FROM sale AS s
JOIN calendar_day AS d USING (sale_date)
JOIN store AS a USING (store_id)
JOIN product AS p USING (product_id)
JOIN product_group AS g USING (group_id);

CREATE VIEW IF NOT EXISTS sales_latest_four_months AS
SELECT * FROM sales_for_cube
WHERE sale_date >= date((SELECT max(sale_date) FROM sale), 'start of month', '-3 months');

CREATE VIEW IF NOT EXISTS sales_by_month AS
SELECT year_month, store_name, group_name,
       sum(quantity) AS quantity, sum(amount_cents) / 100.0 AS amount
FROM sales_for_cube
GROUP BY year_month, store_name, group_name;
