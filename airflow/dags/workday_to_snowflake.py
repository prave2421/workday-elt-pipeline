"""
Workday → Snowflake → dbt ELT Pipeline

Flow:
  simulate_changes (optional)
    → extract_workers → extract_job_changes → extract_compensation
      → load_raw
        → dbt_refined → dbt_curated → dbt_test
"""

import glob
import json
import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

sys.path.insert(0, "/opt/airflow")
from include.extract.workday_client import extract_endpoint, simulate_changes


ENDPOINTS = ["workers", "positions", "organizations", "compensation", "time_off", "job_changes"]

DBT_ENV = {
    "SNOWFLAKE_ACCOUNT": os.environ.get("SNOWFLAKE_ACCOUNT", ""),
    "SNOWFLAKE_USER": os.environ.get("SNOWFLAKE_USER", ""),
    "SNOWFLAKE_ROLE": os.environ.get("SNOWFLAKE_ROLE", ""),
    "SNOWFLAKE_WAREHOUSE": os.environ.get("SNOWFLAKE_WAREHOUSE", ""),
    "SNOWFLAKE_DATABASE": os.environ.get("SNOWFLAKE_DATABASE", ""),
    "SNOWFLAKE_PRIVATE_KEY_PATH": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", "/opt/airflow/snowflake_rsa_key.p8"),
}


def get_snowflake_conn():
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", "/opt/airflow/snowflake_rsa_key.p8")
    with open(key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend(),
        )

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=private_key_bytes,
        role=os.environ.get("SNOWFLAKE_ROLE", "ELT_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "WORKDAY_DB"),
    )


def task_simulate(**context):
    """Simulate workforce changes before extraction."""
    result = simulate_changes(num_events=10)
    return result


def task_extract(endpoint: str, **context):
    """Extract a single endpoint from mock Workday API."""
    load_date = context["ds"]
    output_dir = extract_endpoint(
        endpoint=endpoint,
        load_date=load_date,
        updated_since=None,  # Full load for POC; switch to incremental with XCom state
    )
    return output_dir


def task_load_raw(**context):
    """Load all extracted JSON files into Snowflake RAW tables."""
    load_date = context["ds"]
    conn = get_snowflake_conn()
    cur = conn.cursor()

    try:
        for endpoint in ENDPOINTS:
            table_name = f"WORKDAY_DB.RAW.{endpoint.upper()}"
            stage_name = f"WORKDAY_DB.RAW.{endpoint.upper()}_STAGE"

            # Create table + stage
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    raw_data    VARIANT,
                    _loaded_at  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    _file_name  VARCHAR,
                    _source     VARCHAR DEFAULT '{endpoint}'
                )
            """)

            cur.execute(f"""
                CREATE STAGE IF NOT EXISTS {stage_name}
                    FILE_FORMAT = (TYPE = 'JSON' STRIP_OUTER_ARRAY = TRUE)
            """)

            # Find extracted files
            landing_dir = f"/opt/airflow/data/landing/{endpoint}/load_date={load_date}"
            json_files = glob.glob(f"{landing_dir}/*.json")

            if not json_files:
                print(f"  [{endpoint}] No files to load")
                continue

            for f in json_files:
                put_sql = f"PUT 'file://{f}' @{stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
                print(f"  [{endpoint}] PUT: {f}")
                cur.execute(put_sql)

            cur.execute(f"""
                COPY INTO {table_name} (raw_data, _loaded_at, _file_name, _source)
                FROM (
                    SELECT
                        $1::VARIANT,
                        CURRENT_TIMESTAMP(),
                        METADATA$FILENAME,
                        '{endpoint}'
                    FROM @{stage_name}
                )
                FILE_FORMAT = (TYPE = 'JSON' STRIP_OUTER_ARRAY = TRUE)
                ON_ERROR = 'CONTINUE'
            """)

            result = cur.fetchall()
            print(f"  [{endpoint}] COPY INTO result: {result}")

    finally:
        cur.close()
        conn.close()


# --- DAG ---
default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="workday_to_snowflake",
    default_args=default_args,
    description="Mock Workday → Snowflake RAW → dbt REFINED → CURATED (SCD2)",
    schedule="@daily",
    start_date=datetime(2026, 9, 25),
    catchup=False,
    tags=["elt", "snowflake", "dbt", "workday", "scd2"],
) as dag:

    simulate = PythonOperator(
        task_id="simulate_changes",
        python_callable=task_simulate,
    )

    extract_tasks = []
    for ep in ENDPOINTS:
        task = PythonOperator(
            task_id=f"extract_{ep}",
            python_callable=task_extract,
            op_kwargs={"endpoint": ep},
        )
        extract_tasks.append(task)

    load_raw = PythonOperator(
        task_id="load_to_snowflake_raw",
        python_callable=task_load_raw,
    )

    dbt_refined = BashOperator(
        task_id="dbt_refined",
        bash_command="cd /opt/airflow/dbt && dbt run --select refined --profiles-dir .",
        env=DBT_ENV,
    )

    dbt_curated = BashOperator(
        task_id="dbt_curated",
        bash_command="cd /opt/airflow/dbt && dbt run --select curated --profiles-dir .",
        env=DBT_ENV,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/airflow/dbt && dbt test --profiles-dir .",
        env=DBT_ENV,
    )

    simulate >> extract_tasks >> load_raw >> dbt_refined >> dbt_curated >> dbt_test
