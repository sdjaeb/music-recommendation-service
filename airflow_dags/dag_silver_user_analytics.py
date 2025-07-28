from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

with DAG(
    dag_id="silver_user_analytics_processing",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["silver", "analytics"],
    doc_md="""
    ### Silver User Analytics Processing DAG

    This DAG runs a Spark job to calculate user engagement metrics.
    It reads from Bronze and Silver tables and writes a new summary
    table to the Silver layer.
    """,
) as dag:
    # Task to process user analytics and save to a Silver table
    process_user_analytics = SparkSubmitOperator(
        task_id="process_user_analytics_summary",
        application="/opt/airflow/pyspark_jobs/process_user_analytics.py",
        conn_id="spark_default",
        application_args=[
            "--data-bucket",
            "data",
        ],
        packages="org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,io.delta:delta-spark_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.4",
        conf={
            "spark.driver.memory": "2g",
        },
        verbose=True,
    )