-- Série mensal tipada, com calendário completo gerado à parte para detectar meses faltantes.
create or replace table stg_monthly_sales as
with cal as (
    select cast(range as date) as month
    from range((select min(cast(ds as date)) from raw_sales),
               (select max(cast(ds as date)) from raw_sales) + interval 1 month, interval 1 month)
)
select c.month, cast(r.y as double) as sales
from cal c left join raw_sales r on cast(r.ds as date) = c.month
order by c.month;
