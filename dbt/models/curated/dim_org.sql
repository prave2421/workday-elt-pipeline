/*
    Organization dimension with hierarchy.
*/

WITH source AS (
    SELECT
        raw_data:id::VARCHAR            AS org_id,
        raw_data:name::VARCHAR          AS org_name,
        raw_data:parent_id::VARCHAR     AS parent_org_id,
        raw_data:type::VARCHAR          AS org_type
    FROM {{ source('raw', 'organizations') }}
),

deduped AS (
    SELECT DISTINCT *
    FROM source
)

SELECT
    MD5(org_id) AS org_key,
    org_id,
    org_name,
    parent_org_id,
    org_type,
    -- Self-join for parent name
    parent.org_name AS parent_org_name
FROM deduped
LEFT JOIN deduped parent ON deduped.parent_org_id = parent.org_id
