# airflow_dags/dag_silver_processing.py
from datetime import datetime, timedelta
from airflow.models.dag import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

# --- Constants ---
SPARK_PACKAGES = "org.apache.hadoop:hadoop-aws:3.3.4,io.delta:delta-spark_2.12:3.2.0"

with DAG(
    dag_id="silver_layer_processing",
    start_date=datetime(2025, 1, 8), # Start after the first weekly data is available
    schedule=timedelta(days=1),
    catchup=False,
    tags=["data-processing", "spark", "minio", "silver-layer"],
    doc_md="""
    ### Silver Layer Processing DAG

    This DAG orchestrates the transformation of data from the Bronze layer to the Silver layer.
    It runs Spark jobs to create cleaned, aggregated, and enriched datasets ready for analytics
    and machine learning.

    - **process_trending_tracks**: Calculates the top trending tracks over the last 7 days.
    """
) as dag:
    
    process_trending_tracks = SparkSubmitOperator(
        task_id="process_silver_trending_tracks",
        application="/opt/airflow/pyspark_jobs/process_silver_trending_tracks.py",
        py_files="/opt/airflow/pyspark_jobs/spark_utils.py",
        conn_id="spark_default",
        packages=SPARK_PACKAGES,
        verbose=True,
        conf={
            "spark.pyspark.driver.python": "python3",
            "spark.pyspark.python": "/usr/local/bin/python3",
        },
    )