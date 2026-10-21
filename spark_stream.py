import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

schema = StructType([
    StructField("patient_id", StringType(), True),
    StructField("device_id", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("heart_rate_bpm", IntegerType(), True),
    StructField("prediction", StringType(), True),
    StructField("class_id", IntegerType(), True),
    StructField("confidence", FloatType(), True),
    StructField("alert_status", StringType(), True),
    StructField("lead_ii_signal", StringType(), True)
])

def create_spark_connection():
    try:
        spark = SparkSession.builder \
            .appName("ECGArrhythmiaStreaming") \
            .config("spark.cassandra.connection.host", "cassandra") \
            .config("spark.cassandra.connection.port", "9042") \
            .getOrCreate()
        spark.sparkContext.setLogLevel("ERROR")
        logger.info("[+] Spark session initialized successfully")
        return spark
    except Exception as e:
        logger.error(f"[-] Could not create Spark session: {e}")
        return None

def connect_to_kafka(spark_conn):
    try:
        df = spark_conn.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "broker:29092") \
            .option("subscribe", "ecg_telemetry") \
            .option("startingOffsets", "latest") \
            .load()
        logger.info("[+] Connected to Kafka topic 'ecg_telemetry'")
        return df
    except Exception as e:
        logger.error(f"[-] Kafka connection failed: {e}")
        return None

if __name__ == "__main__":
    spark = create_spark_connection()
    if spark:
        kafka_df = connect_to_kafka(spark)
        if kafka_df:
            parsed_df = kafka_df.selectExpr("CAST(value AS STRING)") \
                .select(from_json(col("value"), schema).alias("data")) \
                .select("data.*")

            # Write stream directly to Cassandra table
            query = parsed_df.writeStream \
                .format("org.apache.spark.sql.cassandra") \
                .option("checkpointLocation", "/tmp/ecg_checkpoint") \
                .option("keyspace", "spark_streams") \
                .option("table", "ecg_patient_alerts") \
                .start()

            logger.info("[*] Streaming pipeline active: Kafka -> Spark -> Cassandra")
            query.awaitTermination()