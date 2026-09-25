{{
    config(
        materialized='incremental',
        unique_key='compensation_id',
        on_schema_change='sync_all_columns'
    )
}}

WITH source AS (
    SELECT raw_data, _loaded_at, _file_name
    FROM {{ source('raw', 'compensation') }}
    {% if is_incremental() %}
        WHERE _loaded_at > (SELECT MAX(_loaded_at) FROM {{ this }})
    {% endif %}
),

flattened AS (
    SELECT
        raw_data:compensation_id::VARCHAR       AS compensation_id,
        raw_data:worker_id::VARCHAR             AS worker_id,
        raw_data:effective_date::DATE           AS effective_date,
        raw_data:compensation_type::VARCHAR     AS compensation_type,
        raw_data:currency::VARCHAR              AS currency,
        raw_data:base_salary::FLOAT             AS base_salary,
        raw_data:bonus_target_pct::FLOAT        AS bonus_target_pct,
        raw_data:bonus_target_amount::FLOAT     AS bonus_target_amount,
        raw_data:total_compensation::FLOAT      AS total_compensation,
        raw_data:pay_frequency::VARCHAR         AS pay_frequency,
        raw_data:created_at::TIMESTAMP_NTZ      AS source_created_at,
        raw_data:updated_at::TIMESTAMP_NTZ      AS source_updated_at,
        _loaded_at,
        _file_name
    FROM source
),

deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY compensation_id ORDER BY _loaded_at DESC) AS rn
    FROM flattened
)

SELECT * EXCLUDE (rn) FROM deduped WHERE rn = 1
