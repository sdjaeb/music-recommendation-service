# Demo Checklist: End-to-End Data Platform

This document provides a step-by-step checklist for demonstrating the core features of the music recommendation data platform. It's designed to be followed sequentially to showcase our progress and capabilities.

---

### Introduction

*"Alright team, welcome to the demo of our new data platform. The goal today is to walk through the core ingestion capabilities we've built, showing how we handle both a large historical data load and ongoing, incremental updates. We'll follow this checklist to keep us on track."*

---

## Part 1: Platform Spin-Up and Health Check

*"First things first, let's get the entire platform running and verify all the components are healthy."*

-   [ ] **Step 1: Start the Services.**
    -   **Action:** Run the single command to bring all services online.
    -   **Command:** `docker-compose up --build -d`

-   [ ] **Step 2: Verify Services are Healthy.**
    -   **Action:** Do a quick tour of the service UIs to confirm everything is online. This is our command center.
    -   **Verification Points:**
        -   **Airflow (Orchestration):** `http://localhost:8080` - "This is where we manage our data pipelines."
        -   **Spark Master (Processing):** `http://localhost:8081` - "This shows our Spark cluster is alive and has workers ready for jobs."
        -   **MinIO (Data Lake Storage):** `http://localhost:9001` - "This is our data lake. We'll log in with `minioadmin`/`minioadmin`."
        -   **Grafana (Observability):** `http://localhost:3000` - "Our dashboard for metrics and logs."
        -   **Spark Application UI (Live Jobs):** `http://localhost:4040` - "While a Spark job is running from Airflow, we can monitor its progress live here."
        -   **Spark History Server (Job Analysis):** `http://localhost:18080` - "For digging into the details of completed Spark jobs."

---

## Part 2: Phase 1.1 - Historical Data Ingestion (The "Big Bang" Load)

*"Our first scenario is ingesting a full year of historical data. This seeds our data lake with a rich, foundational dataset."*

-   [ ] **Step 1: Generate Historical Data.**
    -   **Action:** Run the script to generate the 2024 dataset.
    -   **Command (Sample):** `python generate_seed_data.py --sample`
    -   **Command (Full):** `python generate_seed_data.py`
    -   **Demo Note:** *"The full data generation is powerful but can take over an hour and create a very large file. For our demo today, we'll use the `--sample` flag, which creates a smaller 30-day dataset instantly. This is also the recommended approach for quick local development."*
    -   **Verification:** "We can see the `generated_data` directory is now populated with our 2024 dataset CSVs."

-   [ ] **Step 2: Run the Ingestion DAG.**
    -   **Action:** Trigger the `initial_data_load` DAG. This pipeline will upload the raw files and then process them with Spark.
    -   **Instructions:** In the Airflow UI, unpause and trigger the `initial_data_load` DAG. The necessary connections are created automatically. The first task will also create the `landing` and `data` buckets in MinIO if they don't exist.

-   [ ] **Step 3: Verify the Results.**
    -   **Action:** Check that the data has landed and been processed correctly.
    -   **Verification Points:**
        -   **Airflow:** "The DAG run should show all green, indicating success."
        -   **MinIO Landing Zone:** "In the `landing` bucket, we can see the raw CSVs under the `historical_data/` prefix."
        -   **MinIO Bronze Layer:** "And most importantly, in the `data` bucket, we now have a `bronze/` directory containing our new Delta tables. This is our 'Bronze' layer—the raw, validated source of truth for our data lake."

---

## Part 3: Phase 1.2 - Incremental Weekly Ingestion (The "Steady State")

*"The historical data is in. Now let's simulate a new week of data arriving for 2025 to show how we handle ongoing, incremental updates."*

-   [ ] **Step 1: Generate a New Weekly File.**
    -   **Action:** Run the script to generate the first week of 2025 data.
    -   **Command:** `python generate_weekly_trends.py`
    -   **Verification:** "A new file, `trends_2025-01-07.csv`, has appeared in `generated_data/weekly_trends/`."

-   [ ] **Step 2: Run the Weekly Ingestion DAG.**
    -   **Action:** Trigger the `weekly_trends_ingestion` DAG. For the demo, we'll trigger it manually, but this would normally run on a schedule.
    -   **Instructions:** In the Airflow UI, unpause and trigger the `weekly_trends_ingestion` DAG.

-   [ ] **Step 3: Verify the Results.**
    -   **Action:** Confirm the new data was appended correctly to our main fact table.
    -   **Verification Points:**
        -   **Airflow:** "The weekly DAG run is successful."
        -   **MinIO Landing Zone:** "The new `trends_...csv` file is now in the `landing/weekly_trends/` path."
        -   **MinIO Bronze Layer:** "The `fact_listening_events` Delta table has been updated. We can verify this by looking at the transaction log (`_delta_log`) which shows a new version, or by running a query to count records where `year=2025`."

---

## Part 4: Phase 2.1 - Silver Layer Processing (Analytics)

*"Now that we have our raw Bronze data, let's create our first analytical table. We'll run a pipeline that calculates the top trending tracks from the last 7 days and saves them to a new 'Silver' table."*

-   [ ] **Step 1a: Run the Weekly Trends DAG.**
    -   **Action:** Trigger the `silver_layer_processing` DAG.
    -   **Instructions:** In the Airflow UI, unpause and trigger the `silver_layer_processing` DAG. While it's running, we can monitor the live Spark job in the Spark Application UI at `http://localhost:4040`.

-   [ ] **Step 1b: Run the Song Similarity DAG.**
    -   **Action:** Trigger the `silver_song_similarity_processing` DAG.
    -   **Demo Note:** *"Next, we'll compute another critical analytical table for our recommendation engine. This job finds pairs of songs that are frequently added to the same playlists by users, which is a powerful signal for 'what to play next'."*
    -   **Instructions:** In the Airflow UI, unpause and trigger the `silver_song_similarity_processing` DAG.

-   [ ] **Step 1c: Run the Collaborative Filtering DAG.**
    -   **Action:** Trigger the `silver_collaborative_filtering_processing` DAG.
    -   **Demo Note:** *"Finally, we'll compute our most powerful signal: collaborative filtering. This job analyzes the entire user listening history to find which songs are liked by the same groups of people, creating an item-item similarity score."*
    -   **Instructions:** In the Airflow UI, unpause and trigger the `silver_collaborative_filtering_processing` DAG.

-   [ ] **Step 2: Verify the Silver Layer Results.**
    -   **Action:** Confirm the new aggregated table has been created in the Silver layer.
    -   **Verification Points:**
        -   **Airflow:** "All three Silver Layer DAG runs, `silver_layer_processing`, `silver_song_similarity_processing`, and `silver_collaborative_filtering_processing`, are successful."
        -   **MinIO Silver Layer:** "In the `data` bucket, we now have a `silver/` directory. Inside, we can see all of our new analytical tables:"
            -   **`weekly_trending_tracks`:** "This table contains the aggregated weekly play counts."
            -   **`song_similarity_by_playlist`:** "And this one contains the co-occurrence scores for song pairs."
            -   **`song_collaborative_filtering`:** "This new table contains our item-item collaborative filtering scores."
        -   **Demo Note:** *"These Silver tables are cleaned, aggregated, and ready for direct use by our analytics dashboards and the recommendation model. They represent a single source of truth for these specific business concepts."*

---

## Part 4.5: Data Quality Gates

*"A reliable platform needs to protect itself from bad data. We've integrated Great Expectations to act as a 'quality gate' between our Bronze and Silver layers. Let's look at the `silver_collaborative_filtering_processing` DAG run."*

-   [ ] **Step 1: Inspect the Airflow Task Logs.**
    -   **Action:** In the Airflow UI, navigate to the latest successful run of the `silver_collaborative_filtering_processing` DAG and view the logs for the `run_spark_job` task.
    -   **Verification:** "Right after reading the bronze data, you can see new log output: 'Running data quality checks...' followed by 'Validation successful...'. This confirms our rules were executed. If the source data had been invalid—for example, containing null `user_id`s—this task would have failed, preventing corrupted data from reaching our Silver layer."

---

## Part 5: Ad-Hoc Data Exploration with Jupyter

*"Now that we have processed data in our Silver layer, we can use a Jupyter Notebook for ad-hoc analysis, data science experimentation, or debugging our data pipelines. This demonstrates the platform's flexibility for interactive workloads."*

-   [ ] **Step 1: Access the JupyterLab Interface.**
    -   **Action:** Open a web browser and navigate to the JupyterLab UI.
    -   **URL:** `http://localhost:8888`
    -   **Verification:** "You should see the JupyterLab interface. The first time you access it, you may need to copy a token from the `docker-compose logs jupyter-notebook` output into the password field."

-   [ ] **Step 2: Create and Run a Notebook.**
    -   **Action:** Inside the `notebooks` directory, create a new Python 3 notebook.
    -   **Demo Note:** *"Our Jupyter environment is pre-configured to connect to our Spark cluster and has access to the same helper utilities as our batch jobs. This allows for a seamless transition between development and production."*
    -   **Code:** Copy and paste the following code into a cell and run it.
        ```python
        # In a new Jupyter notebook cell:
        from pyspark_jobs.spark_utils import get

---

## Part 6: Business Intelligence with Grafana

*"The final piece of our analytics layer is a business intelligence dashboard. This allows stakeholders to monitor key metrics without writing any code. It demonstrates how the platform serves not just data scientists, but business users as well."*

-   [ ] **Step 1: Access the Grafana UI.**
    -   **Action:** Open a web browser and navigate to the Grafana UI.
    -   **URL:** `http://localhost:3000`
    -   **Verification:** "You should see the Grafana home page. Our new 'Music Service Analytics' dashboard has been automatically provisioned."

-   [ ] **Step 2: View the Dashboard.**
    -   **Action:** Click on the "Music Service Analytics" dashboard.
    -   **Verification:** "This panel is executing a live SQL query against our Spark cluster, which in turn is reading the `weekly_trending_tracks` Delta table directly from our data lake in MinIO. This shows the full, end-to-end integration from data processing to BI visualization."

---

## Part 7: Using the Recommendation Service

-   [ ] **Step 1: Identify an Active User.**
    -   **Action:** For the demo, we'll use a known active user ID.
    -   **Demo Note:** *"To get a good recommendation, we need a user who is active and has 'liked' songs. We'll use a pre-identified active user for this part of the demo, for example, user `123`."*

-   [ ] **Step 2: Call the Recommendation Endpoint.**
    -   **Action:** Use `curl` or a web browser to make a GET request to the service.
    -   **Demo Note:** *"Now we can see our hybrid model in action. We'll call each of our model endpoints individually to see their results, and then call the main endpoint to see how they're combined."*
    -   **Command (Trending):** `curl http://localhost:8088/recommendations/trending`
    -   **Verification (Trending):** "First, the simplest model: global popularity. These are the top trending tracks across all users."
    -   **Command (Playlist Similarity):** `curl http://localhost:8088/recommendations/similar/123`
    -   **Verification (Playlist Similarity):** "Next, a personalized model based on playlist co-occurrence. These are songs that frequently appear in the same playlists as songs user 123 has liked."
    -   **Command (Collaborative Filtering):** `curl http://localhost:8088/recommendations/collaborative/123`
    -   **Verification (Collaborative Filtering):** "Now for our most powerful model: collaborative filtering. These are songs that users similar to user 123 have also liked. This is a very strong signal."
    -   **Command (Hybrid):** `curl http://localhost:8088/recommendations/123`
    -   **Verification (Hybrid):** "Finally, the main hybrid endpoint. This combines all the previous signals using different weights. The result is a highly relevant, personalized list of recommendations. This demonstrates the power of our end-to-end pipeline, from raw data to sophisticated, model-driven insights."
    - **Example Success Output:**
        ```json
        [54321, 98765, 12345, 67890, 11223]
        ```
    -   **Verification (Not Found):** "If we try a user with no history, like `99999`, we get a `404 Not Found`, which is the correct behavior."
    -   **Command:** `curl -i http://localhost:8088/recommendations/99999`

-   [ ] **Step 3: Verify the Kafka Event.**
    -   **Action:** Check that a `music_recommendations` event was produced to Kafka.
    -   **Demo Note:** *"A key feature of our architecture is that every successful recommendation also generates an event. This allows other downstream systems to react. Crucially, this event is now produced in a binary Avro format, enforced by our Schema Registry. This guarantees data quality at the source."*
    -   **Command (in a separate terminal):** `docker-compose exec kcat kcat -b kafka:29092 -t music_recommendations -C -o end -e`
    -   **Verification:** "After we called the endpoint for user 123, we can see the corresponding event was published to Kafka. Notice that the output from `kcat` is no longer human-readable JSON. It's binary Avro data. This is exactly what we want. It means our producer is correctly serializing the data according to the schema, and any consumer that doesn't adhere to this schema will fail. This is how we prevent data corruption before it even starts."

---

## Part 8: Next Steps (Roadmap Preview)

-   [ ] **Phase 2: Silver Layer & Hybrid Recommendations.** "Our next step is to build on this bronze data. We'll continue creating cleaned, aggregated 'Silver' tables—like song similarity—which are enriched and ready for business analysis. These tables will directly feed a much more sophisticated recommendation model in our .NET service."
-   [ ] **Phase 3: Analytics & Maturity.** "Finally, we'll add a Jupyter notebook for ad-hoc data science and build out analytical dashboards in Grafana to monitor business KPIs, not just system health."