{#- $ and wall time per 50-article scoring batch, per backend × model. Port of lakehouse.gold.scoring_cost_per_batch. -#}

with per as (
    select
        batch_id,
        round(avg(score), 3)                                        as mean_score,
        round(avg({{ b2i('parse_ok') }}), 3)                        as parse_ok_rate,
        {{ pct('wall_ms', 0.5) }}                                   as article_wall_ms_p50,
        {{ pct('wall_ms', 0.9) }}                                   as article_wall_ms_p90,
        sum(prompt_tokens)                                          as prompt_tokens,
        sum(completion_tokens)                                      as completion_tokens
    from {{ ref('silver_scoring_requests') }}
    group by batch_id
)

select
    b.batch_id, b.batch_ts_utc, b.backend, b.model, b.label, b.gpu_model, b.concurrency, b.n, b.n_ok,
    p.parse_ok_rate, p.mean_score, b.wall_ms,
    round(b.wall_ms::double / 1000.0 / b.n, 3)                      as wall_s_per_article,
    p.article_wall_ms_p50, p.article_wall_ms_p90, p.prompt_tokens, p.completion_tokens,
    b.price_unit, b.rate_in_usd_per_m, b.rate_out_usd_per_m, b.rate_usd_per_hr, b.est_cost_usd,
    round(b.est_cost_usd / b.n * 1000, 4)                           as est_cost_usd_per_1k_articles,
    b.note,
    sysdate()                                                       as gold_built_at
from {{ ref('silver_scoring_batches') }} b
left join per p on p.batch_id = b.batch_id
order by b.batch_ts_utc
