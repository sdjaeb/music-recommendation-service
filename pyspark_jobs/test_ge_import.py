# pyspark_jobs/test_ge_import.py
from pyspark.sql import SparkSession

print("--- Spark Job: Attempting to import great_expectations ---")

try:
    import great_expectations as gx
    print(f"--- SUCCESS: Imported great_expectations version: {gx.__version__} ---")
except ImportError as e:
    print(f"--- FAILURE: Could not import great_expectations: {e} ---")
    raise

spark = SparkSession.builder.appName("GE_Import_Test").getOrCreate()
print("--- SparkSession created successfully. ---")

data = [("Test Successful!",)]
df = spark.createDataFrame(data, ["status"])
df.show()

print("--- Spark job finished. ---")
spark.stop()

