{{
    config(
        materialized='table'
    )
}}

/*
    SCD Type 2: Worker dimension with full history.
    Each job change creates a new row with effective_from / effective_to dates.
    Current record has effective_to = '9999-12-31' and is_current = TRUE.
*/

WITH worker_base AS (
    SELECT
        worker_id,
        first_name,
        last_name,
        email,
        gender,
        nationality,
        employment_type,
        employment_status,
        hire_date,
        termination_date,
        termination_reason,
        position_id,
        job_title,
        job_level,
        job_family,
        organization_id,
        organization_name,
        work_location,
        manager_id
    FROM {{ ref('stg_workers') }}
),

job_changes AS (
    SELECT
        worker_id,
        change_type,
        effective_date,
        old_position_id,
        new_position_id,
        old_organization_id,
        new_organization_id
    FROM {{ ref('stg_job_changes') }}
    WHERE approval_status = 'Approved'
),

-- Build SCD2 history from job changes
change_history AS (
    SELECT
        jc.worker_id,
        jc.change_type,
        jc.effective_date AS effective_from,
        COALESCE(
            DATEADD('day', -1,
                LEAD(jc.effective_date) OVER (
                    PARTITION BY jc.worker_id ORDER BY jc.effective_date
                )
            ),
            '9999-12-31'::DATE
        ) AS effective_to,
        jc.new_position_id AS position_id,
        jc.new_organization_id AS organization_id,
        ROW_NUMBER() OVER (
            PARTITION BY jc.worker_id ORDER BY jc.effective_date DESC
        ) AS recency_rank
    FROM job_changes jc
),

-- Join with worker base for full dimension
final AS (
    SELECT
        -- Surrogate key for each SCD2 row
        MD5(wb.worker_id || '|' || ch.effective_from::VARCHAR) AS worker_dim_key,
        wb.worker_id,
        wb.first_name,
        wb.last_name,
        wb.email,
        wb.gender,
        wb.nationality,
        wb.employment_type,
        CASE
            WHEN ch.change_type = 'Termination' THEN 'Terminated'
            ELSE 'Active'
        END AS employment_status,
        wb.hire_date,
        wb.termination_date,
        wb.termination_reason,
        COALESCE(ch.position_id, wb.position_id) AS position_id,
        wb.job_title,
        wb.job_level,
        wb.job_family,
        COALESCE(ch.organization_id, wb.organization_id) AS organization_id,
        wb.organization_name,
        wb.work_location,
        wb.manager_id,
        ch.change_type AS last_change_type,
        ch.effective_from,
        ch.effective_to,
        CASE WHEN ch.effective_to = '9999-12-31'::DATE THEN TRUE ELSE FALSE END AS is_current
    FROM worker_base wb
    LEFT JOIN change_history ch ON wb.worker_id = ch.worker_id
)

SELECT * FROM final
