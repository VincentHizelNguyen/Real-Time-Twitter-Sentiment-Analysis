import os
import sys
from dotenv import load_dotenv

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, udf
from pyspark.sql.types import (
    StructType, StructField, StringType, MapType, LongType
)

print("PYTHON_EXECUTABLE =", sys.executable)
print("PYTHON_PATH_HEAD =", sys.path[:3])

def _sentiment_label(text: str) -> str:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer

    if not hasattr(_sentiment_label, "_sia"):
        nltk.download("vader_lexicon", quiet=True)
        _sentiment_label._sia = SentimentIntensityAnalyzer()

    score = _sentiment_label._sia.polarity_scores(text or "")
    c = score.get("compound", 0.0)
    if c >= 0.05:
        return "positive"
    elif c <= -0.05:
        return "negative"
    return "neutral"

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "tweets_raw")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COL = os.getenv("MONGO_COL")

print("KAFKA_BOOTSTRAP =", KAFKA_BOOTSTRAP)
print("TOPIC =", TOPIC)
print("MONGO_DB =", MONGO_DB, "MONGO_COL =", MONGO_COL)

if not MONGO_URI or not MONGO_DB or not MONGO_COL:
    raise RuntimeError("Missing MONGO_URI / MONGO_DB / MONGO_COL in .env")

schema = StructType([
    StructField("tweet_id", StringType(), True),
    StructField("text", StringType(), True),
    StructField("created_at", StringType(), True),
    StructField("lang", StringType(), True),
    StructField("author_id", StringType(), True),
    StructField("conversation_id", StringType(), True),
    StructField("public_metrics", MapType(StringType(), LongType()), True),
    StructField("source", StringType(), True),
])

sentiment_udf = udf(_sentiment_label, StringType())

spark = (
    SparkSession.builder
    .appName("KafkaSparkSentimentToMongo")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.mongodb.write.connection.uri", MONGO_URI)
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

raw = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
    .option("subscribe", TOPIC)
    .option("startingOffsets", "earliest")   # test mode
    .load()
)

parsed = (
    raw.selectExpr("CAST(value AS STRING) AS json_str")
       .select(from_json(col("json_str"), schema).alias("data"))
       .select("data.*")
)

final_df = parsed.withColumn("label", sentiment_udf(col("text")))

query = (
    final_df.writeStream
    .format("mongodb")
    .option("checkpointLocation", "./_checkpoint_tweets_to_mongo")
    .option("database", MONGO_DB)
    .option("collection", MONGO_COL)
    .outputMode("append")
    .start()
)

query.awaitTermination()
