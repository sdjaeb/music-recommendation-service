import os
from pyspark.sql import SparkSession

def get_spark_session(app_name="SparkApplication"):
    """
    Initializes and returns a SparkSession with common configurations for S3 and Delta Lake.
    Credentials for MinIO are read from environment variables.
    """
    access_key_file = os.getenv("MINIO_ACCESS_KEY_FILE")
    secret_key_file = os.getenv("MINIO_SECRET_KEY_FILE")

    if not access_key_file or not secret_key_file:
        raise ValueError("MinIO credentials are not set in environment variables.")

    with open(access_key_file, 'r') as f:
        minio_access_key = f.read().strip()
    with open(secret_key_file, 'r') as f:
        minio_secret_key = f.read().strip()

    spark = (
        SparkSession.builder.appName(app_name)
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", minio_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )
    return spark