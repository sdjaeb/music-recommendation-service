# End-to-End Music Recommendation Data Pipeline

This project is a comprehensive Proof-of-Concept (POC) demonstrating a modern, end-to-end data pipeline. It features a C#/.NET 8 Minimal API as an event source, integrated into a full data engineering ecosystem including Kafka, Spark, Delta Lake, and a complete observability stack.

The primary goal is to showcase proficiency in a wide range of technologies and best practices, including:
-   **Backend Development:** Clean, testable C#/.NET Minimal APIs.
-   **Containerization:** Multi-service application management with Docker and Docker Compose.
-   **Data Engineering:** Real-time event streaming, processing, and storage in a data lake.
-   **Observability:** The "three pillars" of metrics, logs, and traces.
-   **CI/CD:** Automated build, test, and container publishing with GitHub Actions.

## Core Components & Features

*   **Music Recommendation Service:** A .NET 8 Minimal API that serves static recommendations and produces an event to Kafka for each request.
*   **Data Ingestion Service:** A Python FastAPI application that can simulate a high-volume stream of events into the pipeline.
*   **Real-time Streaming:** Apache Kafka serves as the central, durable message bus for all events.
*   **Stream Processing:** An Apache Spark streaming job consumes events from Kafka in real-time, parses them, and writes them to a Delta Lake table.
*   **Data Lake:** MinIO provides S3-compatible object storage, with Delta Lake adding transactional reliability and ACID properties to the raw data.
*   **Orchestration:** Apache Airflow is included for scheduling, monitoring, and managing complex data workflows (e.g., running batch jobs).
*   **Observability Stack:**
    *   **Prometheus:** Collects and stores time-series metrics from all services.
    *   **Grafana:** For visualizing metrics from Prometheus and logs from Loki in powerful dashboards.
    *   **Loki:** Aggregates logs from all containers.
    *   **Jaeger:** Collects and visualizes distributed traces from the FastAPI service.
*   **CI/CD:** A GitHub Actions workflow automatically builds the .NET project, runs unit tests, and publishes the service's Docker image to the GitHub Container Registry on pushes to `main`.

## Tech Stack

| Category          | Technology                                       |
| ----------------- | ------------------------------------------------ |
| **Backend**       | C# / .NET 8 (Minimal API)                        |
| **Streaming**     | Apache Kafka, Zookeeper                          |
| **Processing**    | Apache Spark 3.5                                 |
| **Storage**       | MinIO (S3-compatible), Delta Lake, PostgreSQL    |
| **Orchestration** | Apache Airflow                                   |
| **Observability** | Prometheus, Grafana, Loki, Jaeger, cAdvisor      |
| **Container**     | Docker, Docker Compose                           |
| **CI/CD**         | GitHub Actions                                   |

## Getting Started

### Prerequisites

*   Docker Desktop
*   .NET 8 SDK (for local development/testing)

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/sdjaeb/music-recommendation-service.git
    cd music-recommendation-service
    ```

2.  **Create Secrets:**
    The platform requires several secret files for database passwords, etc. Create a `secrets` directory at the root of the project and populate it with the necessary files (e.g., `minio_user.txt`, `minio_pass.txt`, `postgres_user.txt`, etc.).
    ```bash
    mkdir secrets
    echo "minio" > secrets/minio_user.txt
    echo "minio123" > secrets/minio_pass.txt
    # ... create other required secret files
    ```

3.  **Run the Platform:**
    Use Docker Compose to build and start all services.
    ```bash
    docker-compose up --build -d
    ```

4.  **Create MinIO Bucket:**
    *   Navigate to the MinIO UI at **http://localhost:9001**.
    *   Log in with the credentials you created in the secrets (e.g., `minio` / `minio123`).
    *   Click **Create Bucket** and create a new bucket named `data`.

## How to Use & Verify the Pipeline

1.  **Start the Spark Streaming Job:**
    Open a terminal and submit the streaming job. It will start and wait for data.
    ```bash
    docker exec -it spark-master spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,io.delta:delta-spark_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.6 /opt/bitnami/spark/jobs/process_recommendation_events.py
    ```

2.  **Generate an Event:**
    In a new terminal, call the `MusicRecommendationService` API.
    ```bash
    curl http://localhost:8088/recommendations/101
    ```

3.  **Observe the Pipeline:**
    *   **Spark Console:** You will see the event processed in a micro-batch in the terminal where the Spark job is running.
    *   **MinIO:** Navigate to the MinIO UI. Inside the `data` bucket, you will see a new `bronze/recommendation_events` directory containing your Delta Lake table.
    *   **Kafka:** You can inspect the `music_recommendations` topic using `kcat`:
        ```bash
        docker exec -it kcat kcat -b kafka:29092 -t music_recommendations -C -J -o beginning
        ```

4.  **Query the Data Lake:**
    Run the batch job to read all the data that has been persisted to the Delta table.
    ```bash
    docker exec -it spark-master spark-submit --packages io.delta:delta-spark_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.6 /opt/bitnami/spark/jobs/read_recommendation_events.py
    ```