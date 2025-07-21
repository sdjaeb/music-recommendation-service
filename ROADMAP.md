# Project Roadmap

This document outlines potential next steps and future enhancements for the music recommendation data platform. It's divided into several key areas of development.

## Data Usage & Analytics

The "Bronze" Delta table of recommendation events is the source of truth. The next step is to refine and use this data.

- [ ] **Create "Silver" Aggregated Tables:** Develop a Spark batch job (scheduled by Airflow) that reads from the bronze table, performs aggregations (e.g., count recommendations per track, per user), and saves the results to a "Silver" Delta table.
- [ ] **Build an Analytical Dashboard:** Create a Grafana dashboard that visualizes the data from the Silver table. This could involve using a query engine like Trino/Presto or a Spark Thrift Server to expose the Delta table to Grafana.
- [ ] **Ad-hoc Analysis with Notebooks:** Add a Jupyter Notebook service to the Docker Compose stack to allow for interactive, ad-hoc querying and analysis of the data in MinIO using PySpark.

## New Ingestion Processes

A real-world platform ingests data from many sources. The following are potential new ingestion pipelines to build.

- [ ] **Ingest User Listening History:** Create a new API endpoint (e.g., in the `.NET` service) for users to post their listening history. This data would be produced to a new `user_listening_history` Kafka topic and saved to its own Delta table by a new Spark job.
- [ ] **Ingest Track Metadata:** Develop an Airflow DAG that periodically pulls track metadata (e.g., artist, album, genre) from a public music API (like Spotify's) and stores it in a dimension table in the data lake.
- [ ] **Database Change Data Capture (CDC):** Add a relational database (e.g., another PostgreSQL container) to store user profiles. Use a tool like Debezium to capture changes to the user table and stream them into a `user_profiles` Kafka topic.

## Machine Learning Enhancements

The ultimate goal is to replace the static recommendation logic with a data-driven model.

- [ ] **Train a Collaborative Filtering Model:**
    - [ ] Develop a Spark MLlib batch job that reads the recommendation events and listening history from the data lake.
    - [ ] Use this data to train a collaborative filtering model (e.g., Alternating Least Squares - ALS).
    - [ ] Save the trained model artifacts back to MinIO.
- [ ] **Model Serving:**
    - [ ] Create a new endpoint in the `MusicRecommendationService`.
    - [ ] When a request comes in, the service should load the latest trained model from MinIO.
    - [ ] Use the model to generate dynamic, personalized recommendations for the user.
- [ ] **Implement a Feedback Loop:**
    - [ ] Enhance the event production to capture user feedback on the recommendations (e.g., "did the user play the recommended track?").
    - [ ] Incorporate this feedback data into the model retraining process to continuously improve recommendation quality.

## Platform & Operational Improvements

- [ ] **Schema Management:** Integrate a Schema Registry (like the Confluent Schema Registry) to manage and enforce schemas for Kafka topics, preventing data quality issues.
- [ ] **Data Quality Checks:** Implement data quality checks using a library like `Great Expectations` within an Airflow DAG to validate data as it moves from Bronze to Silver layers.
- [ ] **Advanced CI/CD:** Extend the GitHub Actions workflow to include automated deployment to a staging or production environment (e.g., Kubernetes).