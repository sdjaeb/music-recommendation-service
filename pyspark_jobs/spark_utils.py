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

    builder = SparkSession.builder.appName(app_name)

    # If running in a container with SPARK_MASTER set, connect to it.
    # Otherwise, it will run in local mode (e.g., for local testing).
    spark_master_url = os.getenv("SPARK_MASTER")
    if spark_master_url:
        builder = builder.master(spark_master_url)

    spark = (
        builder
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", minio_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.4")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )
    return spark

def read_delta_table(spark: SparkSession, path: str, base_path: str = "s3a://data"):
    """
    Reads a Delta table from the specified path within the base path.
    Example: read_delta_table(spark, "bronze/my_table")
    """
    full_path = f"{base_path}/{path}"
    print(f"Reading Delta table from: {full_path}")
    return spark.read.format("delta").load(full_path)

def write_to_delta(df, path: str, mode: str = "overwrite", description: str = None, base_path: str = "s3a://data"):
    """
    Writes a DataFrame to a Delta table at the specified path.
    Example: write_to_delta(my_df, "silver/my_table")
    """
    full_path = f"{base_path}/{path}"
    print(f"Writing DataFrame to Delta table: {full_path} with mode '{mode}'")
    writer = df.write.format("delta").mode(mode)

    if description:
        writer = writer.option("description", description)

    if mode == "overwrite":
        writer = writer.option("overwriteSchema", "true")

    writer.save(full_path)