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
    MD5(d.org_id) AS org_key,
    d.org_id,
    d.org_name,
    d.parent_org_id,
    d.org_type,
    p.org_name AS parent_org_name
FROM deduped d
LEFT JOIN deduped p ON d.parent_org_id = p.org_id
