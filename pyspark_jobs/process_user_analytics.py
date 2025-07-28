# pyspark_jobs/process_user_analytics.py
import argparse
from pyspark.sql.functions import col
from spark_utils import get_spark_session

def process_user_analytics(spark, data_bucket):
    """
    Calculates user engagement metrics and saves them to a Silver table.

    This job calculates two key metrics:
    1. total_likes_count: The total number of "like" events per user.
    2. relevant_likes_count: The number of "like" events for tracks that
       are present in the song similarity model.

    The consolidated results are saved to a new 'user_analytics_summary' table
    in the Silver layer, which can be used to power dashboards.
    """
    bronze_path = f"s3a://{data_bucket}/bronze"
    silver_path = f"s3a://{data_bucket}/silver"

    # --- Load DataFrames ---
    print("Loading data from Bronze and Silver layers...")
    listening_df = spark.read.format("delta").load(f"{bronze_path}/fact_listening_events")
    similarity_df = spark.read.format("delta").load(f"{silver_path}/song_similarity_by_playlist")

    # --- Calculate Metrics ---
    print("Calculating user analytics metrics...")
    user_likes_df = listening_df.filter(col("event_type") == "like") \
        .groupBy("user_id") \
        .count() \
        .withColumnRenamed("count", "total_likes_count")

    similar_tracks_1 = similarity_df.select(col("track_id_1").alias("track_id"))
    similar_tracks_2 = similarity_df.select(col("track_id_2").alias("track_id"))
    all_similar_tracks = similar_tracks_1.union(similar_tracks_2).distinct()

    relevant_users_df = listening_df.filter(col("event_type") == "like") \
        .join(all_similar_tracks, "track_id") \
        .groupBy("user_id") \
        .agg({"*": "count"}) \
        .withColumnRenamed("count(1)", "relevant_likes_count")

    consolidated_df = user_likes_df.join(relevant_users_df, "user_id", "left") \
        .na.fill(0, ["relevant_likes_count"]) \
        .select("user_id", "total_likes_count", "relevant_likes_count")

    # --- Write to Silver Layer ---
    output_path = f"{silver_path}/user_analytics_summary"
    print(f"Writing user analytics summary to {output_path}...")
    consolidated_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(output_path)

    print("User analytics processing complete.")
    print("Top 10 users by relevant likes:")
    consolidated_df.orderBy(col("relevant_likes_count").desc()).show(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-bucket", type=str, required=True, help="Name of the MinIO bucket for data.")
    args = parser.parse_args()

    spark = get_spark_session("UserAnalyticsProcessing")
    process_user_analytics(spark, data_bucket=args.data_bucket)
    spark.stop()