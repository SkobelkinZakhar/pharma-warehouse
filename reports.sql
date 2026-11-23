-- Полный набор для куба. Запускай нужный запрос отдельно.
SELECT * FROM sales_for_cube;

-- Срез по методичке: последние четыре календарных месяца относительно данных.
SELECT * FROM sales_latest_four_months;

-- Контроль месячных итогов по аптекам и группам.
SELECT * FROM sales_by_month ORDER BY year_month, store_name, group_name;

-- Группы, которые вместе дают не менее 80% выручки, включая группу на границе.
WITH totals AS (
    SELECT group_name, sum(amount_cents) AS cents FROM sales_for_cube GROUP BY group_name
), ranked AS (
    SELECT *, sum(cents) OVER () AS all_cents,
           sum(cents) OVER (ORDER BY cents DESC, group_name ROWS UNBOUNDED PRECEDING) AS cumulative
    FROM totals
)
SELECT group_name, cents / 100.0 AS amount,
       round(100.0 * cumulative / nullif(all_cents, 0), 2) AS cumulative_percent
FROM ranked
WHERE 5 * (cumulative - cents) < 4 * all_cents
ORDER BY cents DESC, group_name;

-- Загрузка аптек за семь календарных дней до последней даты включительно.
SELECT sale_date, store_name, sum(quantity) AS quantity
FROM sales_for_cube
WHERE sale_date >= date((SELECT max(sale_date) FROM sale), '-6 days')
GROUP BY sale_date, store_name
ORDER BY sale_date, store_name;
