import sys
import pytest
from pyspark.sql import SparkSession
import os

@pytest.fixture(scope="module")
def spark():
  """
  Fixture for creating a SparkSession for local testing purposes.
  
  This fixture sets up a local Spark cluster for testing. It is used to create a SparkSession
  that can be used in the tests. The SparkSession is configured to run locally with a single thread.
  
  Returns:
    SparkSession: A SparkSession configured for local testing.
  """

        # Ensure the environment variables are set correctly
  print(f"PYSPARK_PYTHON: {os.environ['PYSPARK_PYTHON']}")
  print(f"PYSPARK_DRIVER_PYTHON: {os.environ['PYSPARK_DRIVER_PYTHON']}")
  print(f"SPARK_HOME: {os.environ['SPARK_HOME']}")

  #
  spark = (SparkSession.builder
    .appName("local-testing-pytest") 
    # .master("local[*]") 
    .master("spark://spark-master:7077") 
    .getOrCreate())
  return spark

def test_spark_connection(spark):
  """
  Test to check if the SparkSession is created and connected to the local Spark cluster.
  
  Args:
    spark (SparkSession): The SparkSession fixture.
  """
  data = [("Alice", 1), ("Bob", 2), ("Cathy", 3)]
  columns = ["name", "id"]
  # Create DataFrame
  df = spark.createDataFrame(data, columns)
  
  # Perform some transformations
  df = df.withColumn("double_id", df.id * 2)
  df = df.withColumn("name_length", df.name.length())
  
  # Create a temporary view for SQL queries
  df.createOrReplaceTempView("people")
  
  # Run an SQL query
  result_df = spark.sql("SELECT name, double_id FROM people WHERE name_length > 3")
  
  # Collect the results
  result = result_df.collect()
  
  # Expected results
  expected = [("Alice", 2), ("Cathy", 6)]
  
  # Assert the results
  assert result == expected
  df = spark.createDataFrame(data, columns)

  df = df.transform(lambda df: df.withColumn("double_id", df.id * 2))
  assert df.count() == 10

def test_dummy(spark):
  df = spark.createDataFrame([(1, "Hello"), (2, "World")], ["id", "message"])
  df.show()