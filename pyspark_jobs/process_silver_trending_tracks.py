from pyspark.sql.functions import col, count, current_date, date_sub, to_timestamp, lit
from spark_utils import get_spark_session

def main():
    """
    Main ETL function to process bronze data and create the silver weekly_trending_tracks table.
    """
    spark = get_spark_session("SilverLayerProcessing")
    
    bronze_base_path = "s3a://data/bronze"
    silver_base_path = "s3a://data/silver"

    listening_events_path = f"{bronze_base_path}/fact_listening_events"
    songs_path = f"{bronze_base_path}/dim_songs"
    output_path = f"{silver_base_path}/weekly_trending_tracks"

    print(f"Reading listening events from {listening_events_path}")
    listening_events_df = spark.read.format("delta").load(listening_events_path)

    print(f"Reading song dimensions from {songs_path}")
    songs_df = spark.read.format("delta").load(songs_path)

    print("Filtering for recent 'complete_listen' events...")
    recent_listens_df = (
        listening_events_df
        .withColumn("event_timestamp", to_timestamp(col("timestamp")))
        .filter(col("event_timestamp") >= date_sub(current_date(), 7))
        .filter(col("event_type") == "complete_listen")
    )

    print("Aggregating listen counts and joining with song metadata...")
    final_df = (
        recent_listens_df.groupBy("track_id").agg(count("*").alias("listen_count"))
        .join(songs_df, "track_id")
        .select("track_id", col("title").alias("track_name"), col("artist_name"), "listen_count", lit(current_date()).alias("processing_date"))
        .orderBy(col("listen_count").desc())
    )

    print(f"Writing weekly trending tracks to {output_path}")
    final_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(output_path)

    print("Silver layer processing complete.")
    spark.stop()

if __name__ == "__main__":
    main()