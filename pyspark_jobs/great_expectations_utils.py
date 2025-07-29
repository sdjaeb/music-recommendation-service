import great_expectations as gx
from great_expectations.checkpoint import Checkpoint

def validate_spark_df(spark_df, expectation_suite_name, ge_project_root_dir="/opt/airflow/great_expectations"):
    """
    Validates a Spark DataFrame against a Great Expectations suite.

    :param spark_df: The Spark DataFrame to validate.
    :param expectation_suite_name: The name of the expectation suite to use.
    :param ge_project_root_dir: The root directory of the Great Expectations project.
    :return: The validation result object.
    :raises: ValueError if validation fails.
    """
    context = gx.get_context(project_root_dir=ge_project_root_dir, context_root_dir=ge_project_root_dir)

    datasource = context.sources.add_or_update_spark(name="spark_temp_ds")
    data_asset = datasource.add_dataframe_asset(name="temp_asset", dataframe=spark_df)

    checkpoint = Checkpoint(
        name="temp_checkpoint",
        data_context=context,
        validations=[
            {
                "batch_request": data_asset.build_batch_request(),
                "expectation_suite_name": expectation_suite_name,
            },
        ],
    )

    result = checkpoint.run()

    if not result["success"]:
        print("Data quality validation failed!")
        print(result)
        raise ValueError(f"Data quality check for suite '{expectation_suite_name}' failed.")

    print(f"Validation successful for suite '{expectation_suite_name}'!")
    return result