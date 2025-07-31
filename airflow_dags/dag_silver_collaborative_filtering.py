from airflow.models.dag import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime

with DAG(
    dag_id="silver_collaborative_filtering_processing",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # This DAG is manually triggered
    catchup=False,
    tags=['spark', 'silver', 'recommendations'],
    doc_md="""
    ### Silver Collaborative Filtering Processing DAG

    This DAG runs a Spark job to calculate song-song similarity based on user co-likes.
    This is a form of item-item collaborative filtering.
    It reads from the bronze `fact_listening_events` table and writes the aggregated
    results to the `song_collaborative_filtering` silver table.
    """
) as dag:
    process_collaborative_filtering = SparkSubmitOperator(
        task_id="run_spark_collaborative_filtering",
        application="/opt/airflow/pyspark_jobs/process_collaborative_filtering.py",
        py_files="/opt/airflow/pyspark_jobs/spark_utils.py",
        conn_id="spark_default",
        packages="io.delta:delta-spark_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.4",
        verbose=True,
    )