FROM apache/airflow:2.10.4-python3.11

USER airflow

# Install Snowflake connector + Airflow provider first
RUN pip install --no-cache-dir \
    apache-airflow-providers-snowflake \
    snowflake-connector-python[pandas] \
    cryptography \
    requests

# Install dbt separately to avoid conflicts
RUN pip install --no-cache-dir --no-deps dbt-snowflake dbt-core dbt-adapters dbt-common dbt-events dbt-extractor dbt-state || \
    pip install --no-cache-dir dbt-snowflake==1.8.4
