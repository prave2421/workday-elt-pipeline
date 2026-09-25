/*
    Compensation fact — salary history per worker.
    Joins with dim_worker for demographic context.
*/

SELECT
    c.compensation_id,
    c.worker_id,
    c.effective_date,
    c.compensation_type,
    c.currency,
    c.base_salary,
    c.bonus_target_pct,
    c.bonus_target_amount,
    c.total_compensation,
    c.pay_frequency,

    -- Worker context at time of comp change
    w.job_title,
    w.job_level,
    w.job_family,
    w.organization_name,
    w.work_location,

    -- Salary change tracking
    LAG(c.base_salary) OVER (
        PARTITION BY c.worker_id ORDER BY c.effective_date
    ) AS previous_base_salary,
    CASE
        WHEN LAG(c.base_salary) OVER (PARTITION BY c.worker_id ORDER BY c.effective_date) IS NOT NULL
        THEN ROUND(
            (c.base_salary - LAG(c.base_salary) OVER (PARTITION BY c.worker_id ORDER BY c.effective_date))
            / LAG(c.base_salary) OVER (PARTITION BY c.worker_id ORDER BY c.effective_date) * 100, 2
        )
    END AS salary_change_pct,

    c._loaded_at
FROM {{ ref('stg_compensation') }} c
LEFT JOIN {{ ref('dim_worker') }} w
    ON c.worker_id = w.worker_id
    AND w.is_current = TRUE
