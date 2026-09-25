{{
    config(
        materialized='incremental',
        unique_key='change_id',
        on_schema_change='sync_all_columns'
    )
}}

WITH source AS (
    SELECT raw_data, _loaded_at, _file_name
    FROM {{ source('raw', 'job_changes') }}
    {% if is_incremental() %}
        WHERE _loaded_at > (SELECT MAX(_loaded_at) FROM {{ this }})
    {% endif %}
),

flattened AS (
    SELECT
        raw_data:change_id::VARCHAR             AS change_id,
        raw_data:worker_id::VARCHAR             AS worker_id,
        raw_data:change_type::VARCHAR           AS change_type,
        raw_data:reason::VARCHAR                AS change_reason,
        raw_data:effective_date::DATE           AS effective_date,
        raw_data:old_position_id::VARCHAR       AS old_position_id,
        raw_data:new_position_id::VARCHAR       AS new_position_id,
        raw_data:old_organization_id::VARCHAR   AS old_organization_id,
        raw_data:new_organization_id::VARCHAR   AS new_organization_id,
        raw_data:initiated_by::VARCHAR          AS initiated_by,
        raw_data:approval_status::VARCHAR       AS approval_status,
        raw_data:created_at::TIMESTAMP_NTZ      AS source_created_at,
        raw_data:updated_at::TIMESTAMP_NTZ      AS source_updated_at,
        _loaded_at,
        _file_name
    FROM source
),

deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY change_id ORDER BY _loaded_at DESC) AS rn
    FROM flattened
)

SELECT * EXCLUDE (rn) FROM deduped WHERE rn = 1
