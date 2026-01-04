from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType
from pymongo import MongoClient
import re
from nltk.sentiment import SentimentIntensityAnalyzer

# Spark session
spark = SparkSession.builder \
    .appName("KafkaSparkSentiment") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Kafka stream
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "numtest") \
    .load()

# Kafka value → string
tweets = df.selectExpr("CAST(value AS STRING) as tweet")

# VADER
sia = SentimentIntensityAnalyzer()

def predict_sentiment(text):
    if not text:
        return "Neutral"
    score = sia.polarity_scores(text)["compound"]
    if score >= 0.05:
        return "Positive"
    elif score <= -0.05:
        return "Negative"
    return "Neutral"

def process_batch(batch_df, batch_id):
    client = MongoClient("localhost", 27017)
    collection = client.bigdata_project.tweets

    rows = batch_df.collect()
    for row in rows:
        label = predict_sentiment(row.tweet)
        collection.insert_one({
            "tweet": row.tweet,
            "prediction": label,
            "source": "spark",
            "model": "vader"
        })

# Write stream
query = tweets.writeStream \
    .foreachBatch(process_batch) \
    .start()

query.awaitTermination()
