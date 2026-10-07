-- Vendas anuais (apenas anos completos) e crescimento ano contra ano.
create or replace table mart_yearly as
with y as (
    select year(month) as year, sum(sales) as sales, count(*) as months
    from stg_monthly_sales group by 1
)
select year, sales, round(100 * (sales / lag(sales) over (order by year) - 1), 2) as yoy_pct
from y where months = 12 order by year;

-- Perfil sazonal: quanto cada mês vende em relação à média do próprio ano.
create or replace table mart_month_profile as
with full_years as (
    select year(month) yr from stg_monthly_sales group by 1 having count(*) = 12
), rel as (
    select month(s.month) as month_num, s.sales / avg(s.sales) over (partition by year(s.month)) as rel
    from stg_monthly_sales s join full_years f on year(s.month) = f.yr
)
select month_num, round(100 * avg(rel), 1) as index_vs_year_avg
from rel group by 1 order by 1;
