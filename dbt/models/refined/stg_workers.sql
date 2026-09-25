{{
    config(
        materialized='incremental',
        unique_key='worker_id',
        on_schema_change='sync_all_columns'
    )
}}

/*
    Refined: Flatten nested Workday worker VARIANT into typed columns.
    Handles: personal_data, employment_data, current_position nested objects.
*/

WITH source AS (
    SELECT
        raw_data,
        _loaded_at,
        _file_name
    FROM {{ source('raw', 'workers') }}
    {% if is_incremental() %}
        WHERE _loaded_at > (SELECT MAX(_loaded_at) FROM {{ this }})
    {% endif %}
),

flattened AS (
    SELECT
        -- Identity
        raw_data:worker_id::VARCHAR                             AS worker_id,

        -- Personal data (nested)
        raw_data:personal_data.first_name::VARCHAR              AS first_name,
        raw_data:personal_data.last_name::VARCHAR               AS last_name,
        raw_data:personal_data.email::VARCHAR                   AS email,
        raw_data:personal_data.phone::VARCHAR                   AS phone,
        raw_data:personal_data.date_of_birth::DATE              AS date_of_birth,
        raw_data:personal_data.gender::VARCHAR                  AS gender,
        raw_data:personal_data.nationality::VARCHAR             AS nationality,

        -- Employment data (nested)
        raw_data:employment_data.employment_type::VARCHAR       AS employment_type,
        raw_data:employment_data.status::VARCHAR                AS employment_status,
        raw_data:employment_data.hire_date::DATE                AS hire_date,
        raw_data:employment_data.termination_date::DATE         AS termination_date,
        raw_data:employment_data.termination_reason::VARCHAR    AS termination_reason,

        -- Current position (nested)
        raw_data:current_position.position_id::VARCHAR          AS position_id,
        raw_data:current_position.title::VARCHAR                AS job_title,
        raw_data:current_position.level::VARCHAR                AS job_level,
        raw_data:current_position.job_family::VARCHAR           AS job_family,
        raw_data:current_position.organization_id::VARCHAR      AS organization_id,
        raw_data:current_position.organization_name::VARCHAR    AS organization_name,
        raw_data:current_position.location::VARCHAR             AS work_location,
        raw_data:current_position.manager_id::VARCHAR           AS manager_id,

        -- Metadata
        raw_data:created_at::TIMESTAMP_NTZ                      AS source_created_at,
        raw_data:updated_at::TIMESTAMP_NTZ                      AS source_updated_at,
        _loaded_at,
        _file_name
    FROM source
),

deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY worker_id
            ORDER BY _loaded_at DESC, source_updated_at DESC
        ) AS rn
    FROM flattened
)

SELECT * EXCLUDE (rn) FROM deduped WHERE rn = 1
