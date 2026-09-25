FROM apache/airflow:2.10.4-python3.11

USER airflow

RUN pip install --no-cache-dir \
    apache-airflow-providers-snowflake==5.7.1 \
    snowflake-connector-python==3.12.3 \
    dbt-snowflake==1.9.0 \
    requests==2.32.3 \
    pandas==2.2.3
