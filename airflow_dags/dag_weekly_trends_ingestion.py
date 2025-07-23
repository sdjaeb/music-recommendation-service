# airflow_dags/dag_weekly_trends_ingestion.py
import os
import json
from datetime import datetime, timedelta

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models import Variable

# --- Constants ---
MINIO_CONN_ID = "minio_default"
MINIO_LANDING_BUCKET = "landing"
MINIO_DATA_BUCKET = "data"
LOCAL_WEEKLY_DATA_PATH = "/opt/airflow/data/generated/weekly_trends"
PROCESSED_FILES_VAR_KEY = "processed_weekly_trends_files"

# --- Python Functions for Tasks ---
def upload_new_weekly_files_to_minio(**kwargs):
    """
    Ensures required MinIO buckets exist, scans for new weekly trend files locally,
    uploads them to MinIO, and pushes the list of new S3 paths to XComs.
    """
    s3_hook = S3Hook(aws_conn_id=MINIO_CONN_ID)
    
    for bucket_name in [MINIO_LANDING_BUCKET, MINIO_DATA_BUCKET]:
        if not s3_hook.check_for_bucket(bucket_name=bucket_name):
            s3_hook.create_bucket(bucket_name=bucket_name)
    
    processed_files_str = Variable.get(PROCESSED_FILES_VAR_KEY, default_var="[]")
    processed_files = set(json.loads(processed_files_str))
    
    print(f"Already processed {len(processed_files)} files.")

    if not os.path.exists(LOCAL_WEEKLY_DATA_PATH):
        print(f"Local weekly data directory not found: {LOCAL_WEEKLY_DATA_PATH}")
        return []

    all_local_files = {f for f in os.listdir(LOCAL_WEEKLY_DATA_PATH) if f.endswith('.csv')}
    new_files_to_process = sorted(list(all_local_files - processed_files))

    if not new_files_to_process:
        print("No new weekly trend files to upload.")
        return []

    print(f"Found {len(new_files_to_process)} new files to upload: {new_files_to_process}")
    
    uploaded_s3_paths = []
    for file_name in new_files_to_process:
        local_file_path = os.path.join(LOCAL_WEEKLY_DATA_PATH, file_name)
        minio_object_name = f"weekly_trends/{file_name}"
        s3_path = f"s3a://{MINIO_LANDING_BUCKET}/{minio_object_name}"
        
        print(f"Uploading {local_file_path} to {s3_path}...")
        s3_hook.load_file(
            filename=local_file_path,
            key=minio_object_name,
            bucket_name=MINIO_LANDING_BUCKET,
            replace=True
        )
        uploaded_s3_paths.append(s3_path)
        processed_files.add(file_name)

    Variable.set(PROCESSED_FILES_VAR_KEY, json.dumps(list(processed_files)))
    return uploaded_s3_paths

# --- DAG Definition ---
with DAG(
    dag_id="weekly_trends_ingestion",
    start_date=datetime(2025, 1, 1),
    schedule=timedelta(days=1),
    catchup=False,
    tags=["data-ingestion", "spark", "minio", "incremental"],
    doc_md="""This DAG performs incremental loads of weekly listening trends data."""
) as dag:
    upload_new_files = PythonOperator(
        task_id="upload_new_weekly_files_to_minio",
        python_callable=upload_new_weekly_files_to_minio,
    )
    process_with_spark = SparkSubmitOperator.partial(
        task_id="process_weekly_trend_file_with_spark",
        application="/opt/airflow/pyspark_jobs/process_weekly_trends.py",
        conn_id="spark_default",
        packages="org.apache.hadoop:hadoop-aws:3.3.4,io.delta:delta-spark_2.12:3.2.0",
        verbose=True,
    ).expand(
        application_args=upload_new_files.output.map(lambda s3_path: ["--input-path", s3_path])
    )
    upload_new_files >> process_with_spark
