from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, lit
from spark_utils import get_spark_session, read_delta_table, write_to_delta
from great_expectations_utils import validate_spark_df

def process_collaborative_filtering(spark: SparkSession):
    """
    Calculates song-song similarity based on users who liked both songs.
    This is a form of item-item collaborative filtering.
    """
    # 1. Read the listening events data
    listening_events_df = read_delta_table(spark, "bronze/fact_listening_events")

    # --- NEW: Data Quality Check ---
    # This acts as a "quality gate". If the validation fails, the function
    # will raise an exception, and the Spark job will fail, stopping the pipeline.
    print("Running data quality checks on bronze_fact_listening_events...")
    validate_spark_df(
        spark_df=listening_events_df,
        expectation_suite_name="bronze_fact_listening_events"
    )
    print("Data quality checks passed.")

    # 2. Filter for 'like' events
    likes_df = listening_events_df.filter(col("event_type") == "like").select("user_id", "track_id").distinct()

    # 3. Self-join to find pairs of songs liked by the same user
    # Alias the dataframe to distinguish between the two sides of the join
    likes1 = likes_df.alias("likes1")
    likes2 = likes_df.alias("likes2")

    # Join on user_id, ensuring we don't pair a song with itself
    # and we only get one of (songA, songB) not (songB, songA)
    song_pairs_df = likes1.join(likes2, on="user_id") \
        .where(col("likes1.track_id") < col("likes2.track_id")) \
        .select(
            col("likes1.track_id").alias("track_id_1"),
            col("likes2.track_id").alias("track_id_2")
        )

    # 4. Count co-occurrences to get a similarity score
    similarity_df = song_pairs_df.groupBy("track_id_1", "track_id_2") \
        .agg(count(lit(1)).alias("score"))

    # 5. Write the results to a new Silver Delta table
    write_to_delta(
        df=similarity_df,
        path="silver/song_collaborative_filtering",
        mode="overwrite",
        description="Song similarity scores based on user co-likes (Collaborative Filtering)."
    )

    print("Successfully processed collaborative filtering and created silver table.")

if __name__ == "__main__":
    spark = get_spark_session("ProcessCollaborativeFiltering")
    process_collaborative_filtering(spark)
    spark.stop()