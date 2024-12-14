# Use the Bitnami Spark image as the base image
FROM bitnami/spark:latest



# Copy the test files into the container
COPY /test_local_spark_cluster.py /

# Add the Bitnami Python version to PATH
ENV PATH="/opt/bitnami/python/bin:$PATH"

RUN pip3 install pytest pyspark



# Set the working directory
WORKDIR /

# Command to run the tests
CMD ["python", "-m" "pytest", "test_local_spark_cluster.py"]