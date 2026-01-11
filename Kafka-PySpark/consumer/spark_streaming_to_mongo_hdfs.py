import os
import sys
from dotenv import load_dotenv

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, window,
    length, when, lit, broadcast,
    sum as Fsum
)
from pyspark.sql.types import (
    StructType, StructField, StringType, MapType, LongType
)

print("PYTHON_EXECUTABLE =", sys.executable)
print("PYTHON_PATH_HEAD =", sys.path[:3])

load_dotenv()

# ===== ENV =====
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "tweets_raw")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "bigdata_project")
MONGO_COL_RAW = os.getenv("MONGO_COL_RAW", "tweets_labeled")
MONGO_COL_AGG = os.getenv("MONGO_COL_AGG", "sentiment_agg")

OUTPUT_BASE = os.getenv("OUTPUT_BASE", "file:///C:/bigdata/tweets_parquet")

# checkpoint 
CHK_RAW = os.getenv("CHK_RAW", "C:/bigdata/chk_raw")
CHK_AGG = os.getenv("CHK_AGG", "C:/bigdata/chk_agg")
CHK_BAD = os.getenv("CHK_BAD", "C:/bigdata/chk_bad")

if not MONGO_URI:
    raise RuntimeError("Missing MONGO_URI in .env")

print("KAFKA_BOOTSTRAP =", KAFKA_BOOTSTRAP)
print("TOPIC =", TOPIC)
print("MONGO_DB =", MONGO_DB, "RAW =", MONGO_COL_RAW, "AGG =", MONGO_COL_AGG)
print("OUTPUT_BASE =", OUTPUT_BASE)
print("CHK_RAW =", CHK_RAW)
print("CHK_AGG =", CHK_AGG)
print("CHK_BAD =", CHK_BAD)

# ===== SCHEMA  =====
schema = StructType([
    StructField("tweet_id", StringType(), True),
    StructField("text", StringType(), True),
    StructField("created_at", StringType(), True),  # ISO string
    StructField("lang", StringType(), True),
    StructField("author_id", StringType(), True),
    StructField("conversation_id", StringType(), True),
    StructField("public_metrics", MapType(StringType(), LongType()), True),
    StructField("source", StringType(), True),
])

# ===== Sentiment UDF (VADER) =====
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType as SparkStringType

def _sentiment_label(text: str) -> str:
    """
    IMPORTANT: init nltk + SentimentIntensityAnalyzer LAZY INSIDE UDF
    để tránh serialize object từ driver sang executor (hay chết).
    """
    try:
        import nltk
        from nltk.sentiment import SentimentIntensityAnalyzer

        if not hasattr(_sentiment_label, "_sia"):
          
            nltk.download("vader_lexicon", quiet=True)
            _sentiment_label._sia = SentimentIntensityAnalyzer()

        sia = _sentiment_label._sia
        score = sia.polarity_scores(text or "")
        c = score.get("compound", 0.0)
        if c >= 0.05:
            return "positive"
        elif c <= -0.05:
            return "negative"
        return "neutral"
    except Exception:
        return "neutral"

sentiment_udf = udf(_sentiment_label, SparkStringType())

# ===== Spark Session =====
spark = (
    SparkSession.builder
    .appName("KafkaSparkSentimentToMongoAndLocalFS")
    .config("spark.sql.shuffle.partitions", "8")
    .config("spark.mongodb.write.connection.uri", MONGO_URI)
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# ===== Read Kafka =====
raw_kafka = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
    .option("subscribe", TOPIC)
    .option("startingOffsets", "latest")
    .load()
)

parsed0 = raw_kafka.selectExpr("CAST(value AS STRING) AS json_str")

parsed = (
    parsed0
    .select(from_json(col("json_str"), schema).alias("data"), col("json_str"))
    .select("data.*", "json_str")
)

# Parse created_at ISO-8601 
parsed = parsed.withColumn(
    "event_time",
    to_timestamp(col("created_at"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX")
)

parsed = parsed.withColumn(
    "event_time",
    when(col("event_time").isNull(), to_timestamp(col("created_at"), "yyyy-MM-dd'T'HH:mm:ssX"))
    .otherwise(col("event_time"))
)

# ===== Split good / bad =====
good = parsed.filter(col("tweet_id").isNotNull() & col("text").isNotNull())
bad = parsed.filter(col("tweet_id").isNull() | col("text").isNull())

# ===== basic cleaning + derived features =====
cleaned = (
    good
    .withColumn("text", when(col("text").isNull(), lit("")).otherwise(col("text")))
    .withColumn("text_len", length(col("text")))
    .withColumn("lang", when(col("lang").isNull(), lit("und")).otherwise(col("lang")))
    .withColumn("label", sentiment_udf(col("text")))
    .withColumn("source", when(col("source").isNull(), lit("unknown")).otherwise(col("source")))
)

# ===== Broadcast join requirement =====
lang_dim = spark.createDataFrame(
    [("en", "global"), ("vi", "vn"), ("und", "unknown")],
    ["lang", "region"]
)

enriched = cleaned.join(broadcast(lang_dim), on="lang", how="left")

# ===== Complex Aggregations: watermark + window =====
agg0 = (
    enriched
    .filter(col("event_time").isNotNull())
    .withWatermark("event_time", "10 minutes")
    .groupBy(
        window(col("event_time"), "5 minutes", "1 minute"),
        col("region"),
        col("source")
    )
    .agg(
        Fsum((col("label") == "positive").cast("int")).alias("positive"),
        Fsum((col("label") == "negative").cast("int")).alias("negative"),
        Fsum((col("label") == "neutral").cast("int")).alias("neutral"),
    )
)

# Mongo-friendly
agg = (
    agg0
    .withColumn("window_start", col("window").getField("start"))
    .withColumn("window_end", col("window").getField("end"))
    .drop("window")
)

# ===== foreachBatch writes =====
RAW_PARQUET_PATH = OUTPUT_BASE.rstrip("/") + "/raw_labeled"
BAD_PARQUET_PATH = OUTPUT_BASE.rstrip("/") + "/bad_records"

def write_raw_batch(batch_df, batch_id: int):
    try:
        # 1) Mongo raw
        (
            batch_df.select(
                "tweet_id", "text", "created_at", "event_time", "lang", "region",
                "author_id", "conversation_id", "public_metrics", "source",
                "text_len", "label"
            )
            .write
            .format("mongodb")
            .mode("append")
            .option("database", MONGO_DB)
            .option("collection", MONGO_COL_RAW)
            .save()
        )

        # 2) Parquet raw 
        (
            batch_df.select(
                "tweet_id", "text", "created_at", "event_time", "lang", "region",
                "author_id", "conversation_id", "public_metrics", "source",
                "text_len", "label"
            )
            .write
            .format("parquet")
            .mode("append")
            .partitionBy("source", "region", "label")
            .save(RAW_PARQUET_PATH)
        )

        print(f"[write_raw_batch] batch_id={batch_id} OK rows={batch_df.count()}")
    except Exception as e:
        print(f"[write_raw_batch] batch_id={batch_id} FAILED: {e}")
        raise

def write_agg_batch(batch_df, batch_id: int):
    try:
        (
            batch_df.write
            .format("mongodb")
            .mode("append")
            .option("database", MONGO_DB)
            .option("collection", MONGO_COL_AGG)
            .save()
        )
        print(f"[write_agg_batch] batch_id={batch_id} OK rows={batch_df.count()}")
    except Exception as e:
        print(f"[write_agg_batch] batch_id={batch_id} FAILED: {e}")
        raise

def write_bad_batch(batch_df, batch_id: int):
    try:
        (
            batch_df.select("created_at", "lang", "source", "json_str")
            .write
            .format("parquet")
            .mode("append")
            .save(BAD_PARQUET_PATH)
        )
        print(f"[write_bad_batch] batch_id={batch_id} OK rows={batch_df.count()}")
    except Exception as e:
        print(f"[write_bad_batch] batch_id={batch_id} FAILED: {e}")
        raise

# ===== Start queries =====
q_bad = (
    bad.writeStream
    .queryName("bad_records")
    .foreachBatch(write_bad_batch)
    .option("checkpointLocation", CHK_BAD)
    .outputMode("append")
    .start()
)

q1 = (
    enriched.writeStream
    .queryName("raw_to_mongo_hdfs")
    .foreachBatch(write_raw_batch)
    .option("checkpointLocation", CHK_RAW)
    .outputMode("append")
    .start()
)

q2 = (
    agg.writeStream
    .queryName("agg_to_mongo")
    .foreachBatch(write_agg_batch)
    .option("checkpointLocation", CHK_AGG)
    .outputMode("update")  
    .start()
)

spark.streams.awaitAnyTermination()

