# test_minio_connection.py
# A simple Spark batch job to test the connection to MinIO.
# It creates a small DataFrame and attempts to write it to a Parquet file in MinIO.

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

print("--- Starting MinIO Connection Test ---")
print(f"Read Access Key: {'Yes' if minio_access_key else 'No'}")
print(f"Read Secret Key: {'Yes' if minio_secret_key else 'No'}")

# Initialize a Spark Session with all S3A configurations applied during the build process.
# This is the most reliable method for ensuring the S3A client is configured correctly.
spark = SparkSession.builder \
    .appName("MinIOConnectionTest") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", minio_access_key) \
    .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.committer.name", "directory") \
    .config("spark.hadoop.fs.s3a.committer.staging.conflict-mode", "replace") \
    .config("spark.hadoop.fs.s3a.committer.staging.unique-filenames", "true") \
    .getOrCreate()

print("Hadoop S3A configuration set. Attempting to write to MinIO...")

# Create a sample DataFrame
df = spark.createDataFrame([("test_user", "test_action")], ["user", "action"])

# Define the output path in MinIO
output_path = "s3a://data/test/minio_connection_test"

df.write.mode("overwrite").parquet(output_path)

print(f"--- SUCCESS: Successfully wrote data to {output_path} ---")

spark.stop()
print("--- Test complete. ---")