# airflow_dags/dag_silver_song_similarity.py
from datetime import datetime

from airflow.models.dag import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

# --- Constants ---
MINIO_DATA_BUCKET = "data"

# --- DAG Definition ---
with DAG(
    dag_id="silver_song_similarity_processing",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["silver-layer", "spark", "analytics", "recommendations"],
    doc_md="""
    ### Song Similarity Processing DAG

    This DAG runs a Spark job to calculate song similarity based on playlist co-occurrence.
    It reads the `bridge_playlist_tracks` table from the Bronze layer, computes which
    songs frequently appear together in the same playlists, and writes the aggregated
    scores to the `song_similarity_by_playlist` table in the Silver layer.

    This analytical table is a key input for the hybrid recommendation model.
    """
) as dag:
    calculate_song_similarity = SparkSubmitOperator(
        task_id="calculate_song_similarity_with_spark",
        application="/opt/airflow/pyspark_jobs/process_song_similarity.py",
        conn_id="spark_default",
        packages="org.apache.hadoop:hadoop-aws:3.3.4,io.delta:delta-spark_2.12:3.2.0",
        verbose=True,
        application_args=["--data-bucket", MINIO_DATA_BUCKET],
    )