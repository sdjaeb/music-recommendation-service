# read_recommendation_events.py
# A simple Spark batch job that reads all the data from the 'recommendation_events'
# Delta table stored in MinIO and displays it. This demonstrates how downstream
# analytics or ML jobs would consume data from the data lake.

import os
from pyspark.sql import SparkSession

def read_secret(secret_name):
    secret_path = os.getenv(secret_name)
    if secret_path and os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()
    print(f"Warning: Could not read secret for {secret_name}")
    return None

minio_access_key = read_secret('MINIO_ACCESS_KEY_FILE')
minio_secret_key = read_secret('MINIO_SECRET_KEY_FILE')

DELTA_TABLE_PATH = "s3a://data/bronze/recommendation_events"

print("--- Reading from Delta Lake table in MinIO ---")

spark = SparkSession.builder \
    .appName("ReadRecommendationEvents") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", minio_access_key) \
    .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .getOrCreate()

print(f"Reading data from: {DELTA_TABLE_PATH}")

df = spark.read.format("delta").load(DELTA_TABLE_PATH)

print(f"Successfully read {df.count()} records.")
df.show(truncate=False)

spark.stop()
print("--- Batch job complete. ---")