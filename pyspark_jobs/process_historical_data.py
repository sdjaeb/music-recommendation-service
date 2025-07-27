# pyspark_jobs/process_historical_data.py
from pyspark.sql.functions import col, to_date, year, month
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, LongType,
    FloatType, DateType, TimestampType
)
from spark_utils import get_spark_session

# --- Spark Session Setup ---
spark = get_spark_session("HistoricalDataIngestion")

# --- Configuration ---
LANDING_ZONE_BASE = "s3a://landing/historical_data"
BRONZE_ZONE_BASE = "s3a://data/bronze"

# --- Define Schemas and Processing Logic ---
TABLES_TO_PROCESS = {
    "dim_songs": {
        "schema": StructType([ # Enforce non-nullable keys
            StructField("track_id", LongType(), False), StructField("title", StringType(), True),
            StructField("artist_id", LongType(), False), StructField("artist_name", StringType(), True),
            StructField("genre", StringType(), True), StructField("duration_ms", IntegerType(), True),
            StructField("release_date", DateType(), True), StructField("base_popularity", FloatType(), True)
        ]), "partition_by": None
    },
    "dim_users": {
        "schema": StructType([ # Enforce non-nullable keys
            StructField("user_id", LongType(), False), StructField("user_name", StringType(), True),
            StructField("preferred_genres", StringType(), True), StructField("join_date", DateType(), True)
        ]), "partition_by": None
    },
    "dim_playlists": {
        "schema": StructType([ # Enforce non-nullable keys
            StructField("playlist_id", LongType(), False), StructField("playlist_name", StringType(), True),
            StructField("owner_user_id", LongType(), False), StructField("created_date", DateType(), True)
        ]), "partition_by": None
    },
    "graph_user_follows": {
        "schema": StructType([ # Enforce non-nullable keys
            StructField("user_id_a", LongType(), False), StructField("user_id_b", LongType(), False)
        ]), "partition_by": None
    },
    "bridge_playlist_tracks": {
        "schema": StructType([ # Enforce non-nullable keys
            StructField("playlist_id", LongType(), False), StructField("track_id", LongType(), False)
        ]), "partition_by": None
    },
    "fact_listening_events_2024": {
        "schema": StructType([ # Enforce non-nullable keys
            StructField("event_id", StringType(), False), StructField("user_id", LongType(), False),
            StructField("track_id", LongType(), False), StructField("event_type", StringType(), True),
            StructField("timestamp", TimestampType(), True)
        ]), "partition_by": ["year", "month"], "output_name": "fact_listening_events"
    }
}

# --- Main Processing Loop ---
for table_name, config in TABLES_TO_PROCESS.items():
    input_path = f"{LANDING_ZONE_BASE}/{table_name}.csv"
    output_name = config.get("output_name", table_name)
    output_path = f"{BRONZE_ZONE_BASE}/{output_name}"
    
    print(f"--- Processing {table_name} ---")
    print(f"Reading from: {input_path}")
    
    df = spark.read.csv(input_path, header=True, schema=config["schema"])
    
    # Add partition columns if specified
    if config["partition_by"]:
        df = df.withColumn("event_date", to_date(col("timestamp"))) \
               .withColumn("year", year(col("event_date"))) \
               .withColumn("month", month(col("event_date")))
        
        print(f"Writing to Delta table: {output_path} partitioned by {config['partition_by']}")
        df.write.format("delta").mode("overwrite").partitionBy(*config["partition_by"]).option("overwriteSchema", "true").save(output_path)
    else:
        print(f"Writing to Delta table: {output_path}")
        df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(output_path)
          
    print(f"--- Finished processing {table_name} ---")

print("Historical data ingestion complete.")
spark.stop()