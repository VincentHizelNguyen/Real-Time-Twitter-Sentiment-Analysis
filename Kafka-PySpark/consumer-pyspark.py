import re
import nltk
from kafka import KafkaConsumer
from json import loads
from pymongo import MongoClient
import os

# Windows env 
os.environ["HADOOP_HOME"] = r"C:\Users\thuuy\Real-Time-Twitter-Sentiment-Analysis\Kafka-PySpark\hadoop"
os.environ["SPARK_LOCAL_DIRS"] = r"C:\tmp"

# MongoDB connection
print("1. Kết nối MongoDB...")
client = MongoClient('localhost', 27017)
db = client['bigdata_project']
collection = db['tweets']
print("MongoDB sẵn sàng.\n")

# NLTK
print("2. Download NLTK resources...")
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('vader_lexicon', quiet=True)
print("NLTK sẵn sàng.\n")

# VADER
from nltk.sentiment import SentimentIntensityAnalyzer
sia = SentimentIntensityAnalyzer()
print("3. VADER đã sẵn sàng.\n")

# Clean text cho VADER
def clean_text_vader(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'https?://\S+|www\.\S+|\.com\S+|youtu\.be/\S+', '', text)
    text = re.sub(r'(@|#)\w+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def vader_predict_label(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "Neutral"

    compound = sia.polarity_scores(text)["compound"]  # -1..1
    if compound >= 0.05:
        return "Positive"
    elif compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# Kafka consumer
print("4. Khởi tạo Kafka consumer...")
consumer = KafkaConsumer(
    'numtest',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='my-group',
    value_deserializer=lambda x: loads(x.decode('utf-8'))
)
print("Kafka consumer sẵn sàng.\n")

for message in consumer:
    print("5. Nhận được tweet mới, bước xử lý...")

    # Đọc tweet an toàn 
    val = message.value
    if isinstance(val, list):
        tweet = val[-1] if val else ""
    elif isinstance(val, dict):
        tweet = val.get("tweet") or val.get("text") or val.get("message") or ""
    else:
        tweet = str(val)

    preprocessed_tweet = clean_text_vader(tweet)

    print(f"Raw tweet: {tweet}")
    print(f"Preprocessed tweet: {preprocessed_tweet}")

    label = vader_predict_label(preprocessed_tweet)
    print(f"Prediction class: {label}")

    # Insert into MongoDB
    collection.insert_one({
        "tweet": tweet,
        "clean_tweet": preprocessed_tweet,
        "prediction": label,
        "source": "kafka",
        "model": "vader"
    })
    print("Đã lưu vào MongoDB\n")
