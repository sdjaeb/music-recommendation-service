# airflow_dags/dag_initial_data_load.py
import os
from datetime import datetime
from airflow.models.dag import DAG
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

# --- Constants ---
MINIO_CONN_ID = "minio_default"
MINIO_LANDING_BUCKET = "landing"
MINIO_DATA_BUCKET = "data"
SPARK_PACKAGES = "org.apache.hadoop:hadoop-aws:3.3.4,io.delta:delta-spark_2.12:3.2.0"
LOCAL_DATA_PATH = "/opt/airflow/data/generated"

# --- Python Functions for Tasks ---
def upload_files_to_minio_landing_zone():
    """
    Ensures required MinIO buckets exist, then uploads all generated CSV files
    from a local directory to the 'landing' bucket in MinIO.
    """
    s3_hook = S3Hook(aws_conn_id=MINIO_CONN_ID)
    
    for bucket_name in [MINIO_LANDING_BUCKET, MINIO_DATA_BUCKET]:
        if not s3_hook.check_for_bucket(bucket_name=bucket_name):
            s3_hook.create_bucket(bucket_name=bucket_name)
            print(f"Bucket '{bucket_name}' created.")

    files_to_upload = [f for f in os.listdir(LOCAL_DATA_PATH) if f.endswith('.csv')]
    if not files_to_upload:
        raise AirflowSkipException(f"No CSV files found in {LOCAL_DATA_PATH} to upload. Skipping task.")

    for file_name in files_to_upload:
        local_file_path = os.path.join(LOCAL_DATA_PATH, file_name)
        minio_object_name = f"historical_data/{file_name}"
        
        print(f"Uploading {local_file_path} to {MINIO_LANDING_BUCKET}/{minio_object_name}...")
        s3_hook.load_file(
            filename=local_file_path,
            key=minio_object_name,
            bucket_name=MINIO_LANDING_BUCKET,
            replace=True
        )

    print("All files uploaded successfully.")

# --- DAG Definition ---
with DAG(
    dag_id="initial_data_load",
    start_date=datetime(2024, 1, 1),
    schedule=None,  # This DAG is meant to be triggered manually
    catchup=False,
    tags=["data-ingestion", "spark", "minio"],
    doc_md="""
    ### Initial Data Load DAG

    This DAG performs a one-time load of the historical music data.
    It consists of two main steps:
    1.  **Upload to Landing Zone**: Takes the locally generated CSV files and uploads them to a 'landing' bucket in MinIO.
    2.  **Process with Spark**: Triggers a Spark job to read the raw CSVs from the landing zone, process them, and save them as partitioned Delta tables in the 'bronze' layer of the data lake.
    
    **Note**: The `spark_default` and `minio_default` connections are created automatically from environment variables at startup.
    """
) as dag:
    
    upload_to_landing_zone = PythonOperator(
        task_id="upload_csv_to_minio_landing_zone",
        python_callable=upload_files_to_minio_landing_zone,
    )

    process_with_spark = SparkSubmitOperator(
        task_id="process_historical_data_with_spark",
        application="/opt/airflow/pyspark_jobs/process_historical_data.py",
        py_files="/opt/airflow/pyspark_jobs/spark_utils.py",
        conn_id="spark_default",
        packages=SPARK_PACKAGES,
        verbose=True
    )

    upload_to_landing_zone >> process_with_spark