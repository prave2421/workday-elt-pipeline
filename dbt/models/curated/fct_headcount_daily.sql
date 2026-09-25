/*
    Daily headcount fact — point-in-time snapshot of active workers.
    Uses SCD2 dim_worker to count active employees on each date.
*/

WITH date_spine AS (
    -- Generate dates from earliest hire to today
    SELECT DATEADD('day', ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1,
           (SELECT MIN(hire_date) FROM {{ ref('dim_worker') }})) AS report_date
    FROM TABLE(GENERATOR(ROWCOUNT => 1500))
    QUALIFY report_date <= CURRENT_DATE()
),

headcount AS (
    SELECT
        ds.report_date,
        dw.organization_id,
        dw.organization_name,
        dw.job_family,
        dw.job_level,
        dw.work_location,
        COUNT(DISTINCT dw.worker_id) AS headcount,
        SUM(CASE WHEN dw.last_change_type = 'New Hire'
                  AND dw.effective_from = ds.report_date THEN 1 ELSE 0 END) AS new_hires,
        SUM(CASE WHEN dw.last_change_type = 'Termination'
                  AND dw.effective_from = ds.report_date THEN 1 ELSE 0 END) AS terminations,
        SUM(CASE WHEN dw.last_change_type = 'Promotion'
                  AND dw.effective_from = ds.report_date THEN 1 ELSE 0 END) AS promotions,
        SUM(CASE WHEN dw.last_change_type = 'Transfer'
                  AND dw.effective_from = ds.report_date THEN 1 ELSE 0 END) AS transfers
    FROM date_spine ds
    JOIN {{ ref('dim_worker') }} dw
        ON ds.report_date BETWEEN dw.effective_from AND dw.effective_to
        AND dw.employment_status = 'Active'
    GROUP BY 1, 2, 3, 4, 5, 6
)

SELECT
    MD5(report_date::VARCHAR || '|' || COALESCE(organization_id,'') || '|' ||
        COALESCE(job_family,'') || '|' || COALESCE(work_location,'')) AS headcount_key,
    *
FROM headcount
