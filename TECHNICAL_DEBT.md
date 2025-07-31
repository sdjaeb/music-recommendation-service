# Technical Debt & Architectural Improvements

This document tracks identified areas of the codebase that could benefit from refactoring or architectural changes. These are items that are currently functional but could be improved for better maintainability, testability, and scalability in the future.

---

## 1. Refactor `RecommendationService` with Strategy Pattern

-   **Date Identified:** 2024-08-01
-   **Status:** Pending

### Problem

The `MusicRecommendationService/Services/RecommendationService.cs` class has grown significantly and now contains the business logic for four distinct recommendation models (Hybrid, Similarity, Collaborative, Trending). This violates the Single Responsibility Principle, making the class difficult to read, maintain, and unit test. Data fetching, lookups, and scoring logic are all tightly coupled within single methods.

### Proposed Solution

Refactor the service using the **Strategy design pattern** to decouple each recommendation algorithm into its own class.

**Implementation Steps:**

1.  **Create an `IRecommendationStrategy` interface:** This will define a common contract for all recommendation algorithms (e.g., a method `GetRecommendationsAsync`).
2.  **Implement Concrete Strategies:** Create separate classes for each model, each implementing the new interface:
    -   `PlaylistSimilarityStrategy.cs`
    -   `CollaborativeFilteringStrategy.cs`
    -   `TrendingStrategy.cs`
    -   `HybridRecommendationStrategy.cs` (This would orchestrate the other strategies, combining their results based on configured weights).
3.  **Simplify `RecommendationService`:** The main service will be simplified to a facade that delegates calls to the appropriate strategy. This will also make dependency injection cleaner, as each strategy can declare only the data sources it needs (e.g., `IMinioService` tables).

---

## 2. Update README.md and DEMO_CHECKLIST.md

-   **Date Identified:** 2024-08-01
-   **Status:** Pending

### Problem

The main `README.md` and `DEMO_CHECKLIST.md` have become slightly outdated as the project has evolved. The list of services and their corresponding ports in the documentation does not fully match the `docker-compose.yml` file. This can cause confusion during setup and demos.

### Proposed Solution

Perform a full review of the `README.md` and `DEMO_CHECKLIST.md` files. Update all service URLs, descriptions, and demo steps to align with the current state of the platform. This ensures that documentation is a reliable resource for developers and stakeholders.

---

## 3. Introduce a Vector Database for Advanced Search

-   **Date Identified:** 2024-08-01
-   **Status:** Pending

### Problem

The current project `ROADMAP.md` (Phase 4.1, "Audio Feature Similarity") proposes using a library like Faiss for vector similarity search. While Faiss is excellent for in-memory indexing and rapid prototyping, it presents several challenges for a production-like, evolving platform:
-   **Persistence & Scalability:** Faiss indexes are typically built and loaded into memory, which doesn't scale well with large datasets and requires manual processes for persistence and updates.
-   **Operational Overhead:** Managing the lifecycle of Faiss indexes (building, updating, serving) would require custom infrastructure and code.
-   **Limited Functionality:** It lacks features common in dedicated search databases, such as filtered search (e.g., "find songs with a similar vibe but only from the 1980s"), real-time indexing, and a managed API endpoint.

Additionally, there is currently no simple, command-line interface for developers to perform quick searches on the ingested data without starting a full Jupyter notebook session.

### Proposed Solution

Integrate a dedicated vector database, such as **Weaviate**, to serve as the primary engine for semantic and vector-based search. This would be a direct architectural enhancement to the "Audio Feature Similarity" model outlined in the roadmap.

#### Developer-Facing Search Capabilities

To complement the programmatic API, a command-line interface (CLI) would be developed to provide developers with direct access to the data lake for querying and debugging. This tool would support two distinct search modes:

1.  **Semantic (Vector) Search via Weaviate:**
    *   **Purpose:** For "vibe-based" or similarity queries where a user wants to find music that *sounds like* a given track or matches a natural language description.
    *   **Mechanism:** The CLI would send the query to the Weaviate API. Weaviate would then perform a vector similarity search against its index of song embeddings to find the closest matches based on musical characteristics.
    *   **Example:** `music-cli search vibe --like "Stairway to Heaven"` or `music-cli search vibe --description "instrumental hip-hop for focus"`.

2.  **Metadata (Keyword) Search via Spark SQL:**
    *   **Purpose:** For fast, factual lookups based on specific, known metadata (e.g., artist name, song title).
    *   **Mechanism:** The CLI would establish a connection to the Spark Thrift Server and execute a standard SQL query (e.g., `SELECT * FROM songs WHERE artist = '...'`) against the Delta tables in MinIO.
    *   **Example:** `music-cli search track --artist "Led Zeppelin"`.

This dual-mode approach provides developers with both powerful, ML-driven discovery and precise, high-speed data retrieval capabilities.

**Implementation Steps:**

1.  **Integrate Weaviate:** Add a `weaviate` service to the `docker-compose.yml` stack.
2.  **Update Spark Jobs:** Create or modify a Spark job to:
    -   Generate song embeddings (as planned in Phase 4.1).
    -   Load these embeddings and their associated metadata (song ID, title, artist, genre) into Weaviate.
3.  **Refactor Recommendation Service:** Update the `.NET` `RecommendationService` to query Weaviate's API for similarity-based recommendations instead of a custom Faiss implementation. This simplifies the service and leverages a more powerful backend.
4.  **(Optional) Create a Search CLI:** Develop a simple Python CLI tool (e.g., using `click`) that can perform:
    -   Basic keyword searches against the data in MinIO (via the Spark Thrift Server).
    -   Semantic "vibe" searches against the song embeddings stored in Weaviate.

---

## 4. Great Expectations Integration (Attempted)

-   **Date Identified:** 2025-07-30
-   **Status:** Reverted (Failed Integration)

### Problem

Attempted to integrate Great Expectations (GE) for data quality validation within PySpark jobs orchestrated by Airflow. The primary goal was to add data quality checks on the `bronze_fact_listening_events` table.

### Issues Encountered

1.  **`ModuleNotFoundError: No module named 'great_expectations'`**:
    *   **Initial Cause:** GE was not installed in the Python environment used by Airflow for `spark-submit` operations.
    *   **Attempted Fixes:**
        *   Added `great_expectations` to `requirements-airflow.txt` and rebuilt Airflow images. (Resolved this specific error).
        *   Incorrectly tried to install GE in `Dockerfile.spark-base` via multi-stage build, leading to environment conflicts. (Resolved by installing directly into Bitnami Python path).
    *   **Lesson Learned:** Always verify the exact Python interpreter used by the executing process (Airflow's `spark-submit` vs. Spark worker's PySpark environment). Dependencies for Airflow operators must be in the Airflow environment.

2.  **`AttributeError: 'FileDataContext' object has no attribute 'sources'` / `AttributeError: ... has no attribute 'run_checkpoint'` / `AttributeError: ... has no attribute 'DataContext'`**:
    *   **Cause:** API mismatches with Great Expectations v1.5.6. The code was attempting to use newer "Fluent" APIs (`context.sources.add_spark`, `context.run_checkpoint`) that were not available or were structured differently in the installed GE version.
    *   **Attempted Fixes:** Iteratively refactored `great_expectations_utils.py` to use `RuntimeBatchRequest` and `validator.validate()`, and to correctly instantiate `DataContext` (e.g., `gx.get_context()`).
    *   **Lesson Learned:** Always consult the exact API documentation for the installed library version. Avoid assuming API compatibility across versions.

3.  **`DataContextError: ExpectationSuite with name bronze_fact_listening_events was not found.`**:
    *   **Cause:** Misconfiguration of the Great Expectations project root directory and non-standard project layout. The `great_expectations.yml` file was located in a `gx` subdirectory (`great_expectations/gx`), and the expectation suite JSON file was in a sibling `expectations` directory (`great_expectations/expectations`), rather than the expected `great_expectations/gx/expectations` structure.
    *   **Attempted Fixes:**
        *   Corrected `ge_project_root_dir` in `great_expectations_utils.py` to point to `/opt/bitnami/spark/ge/gx`.
        *   Moved `bronze_fact_listening_events.json` from `great_expectations/expectations` to `great_expectations/gx/expectations`.
    *   **Lesson Learned:** Great Expectations has a strict project structure. Ensure `project_root_dir` points to the directory containing `great_expectations.yml`, and that all other GE artifacts (expectations, checkpoints, data docs) are located in the subdirectories specified in that `great_expectations.yml` file.

4.  **`PermissionError: [Errno 13] Permission denied: '/opt/bitnami'`**:
    *   **Cause:** The user running the Spark job (UID 1001) inside the Docker container lacked write permissions to the `/opt/bitnami` directory or its subdirectories, which Great Expectations attempts to write to for internal operations (e.g., temporary files, caches). Direct `chown` commands within `docker-compose.yml` were problematic due to Docker's bind mount behavior and host filesystem permissions.
    *   **Attempted Fixes:**
        *   Tried `chown -R 1001:0 /opt/bitnami/spark` in `docker-compose.yml` commands (failed due to host permissions).
        *   Tried `chmod -R 777` on the host's `great_expectations` directory (did not resolve the `/opt/bitnami` permission issue).
    *   **Lesson Learned:** For Docker bind mounts, ensure the host directory has appropriate permissions *before* starting the container. If a library tries to write outside the mounted volume to a system directory (like `/opt/bitnami`), it requires root privileges or a different strategy (e.g., configuring the library to use a writable temporary directory). This was the ultimate blocker for this integration attempt.

### Wins

Despite the challenges, this exercise provided valuable insights:

*   **Deepened understanding of Docker/Spark/Airflow interaction:** Clarified the distinct Python environments and execution contexts.
*   **Great Expectations API nuances:** Gained practical experience with version-specific API calls and project structure requirements.
*   **Debugging strategies:** Reinforced the importance of targeted debugging (e.g., `sys.executable`, `sys.path`, `ls -la` inside containers) for complex distributed systems.

### Recommendations for Future Attempts

*   **Standard GE Project Layout:** Adhere strictly to the default Great Expectations project structure (`great_expectations/great_expectations.yml`, `great_expectations/expectations`, etc.) to avoid pathing issues.
*   **Dedicated GE Volume:** Consider mounting a separate Docker volume specifically for Great Expectations' internal data (checkpoints, validation results, data docs) that is explicitly owned and writable by the container user, rather than relying on GE writing directly into the Spark installation directory.
*   **GE Configuration for Temp Dirs:** Investigate Great Expectations configuration options to explicitly set its temporary or cache directories to a location known to be writable by the container user (e.g., `/tmp` or a dedicated writable volume).
*   **Container User Permissions:** For any bind mounts, ensure the host directory's permissions are set such that the container's non-root user has full read/write access.
*   **Test Environment Setup:** Prioritize setting up a minimal, isolated test environment for GE integration before attempting full Airflow/Spark integration.

---
