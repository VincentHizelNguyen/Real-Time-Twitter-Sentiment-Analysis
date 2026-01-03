import os
import time
from dotenv import load_dotenv
import tweepy
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Load .env ở thư mục gốc project
load_dotenv()

BEARER = os.getenv("X_BEARER_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COL = os.getenv("MONGO_COL")

if not BEARER:
    raise RuntimeError("Missing X_BEARER_TOKEN")
if not MONGO_URI or not MONGO_DB or not MONGO_COL:
    raise RuntimeError("Missing MONGO_URI / MONGO_DB / MONGO_COL in .env")

client = tweepy.Client(bearer_token=BEARER, wait_on_rate_limit=True)

mongo = MongoClient(MONGO_URI)
col = mongo[MONGO_DB][MONGO_COL]

# chống trùng tweet
col.create_index([("tweet_id", ASCENDING)], unique=True)
col.create_index([("created_at", ASCENDING)])

# Sentiment (VADER)
nltk.download("vader_lexicon")
sia = SentimentIntensityAnalyzer()

def sentiment_label(text: str) -> str:
    score = sia.polarity_scores(text or "")
    c = score.get("compound", 0.0)

    if c >= 0.05:
        return "positive"
    elif c <= -0.05:
        return "negative"
    else:
        return "neutral"


def to_doc(t):
    pm = t.public_metrics or {}
    label = sentiment_label(t.text)   # <<< label thẳng

    return {
        "tweet_id": str(t.id),
        "text": t.text,
        "created_at": t.created_at,
        "lang": t.lang,
        "author_id": str(t.author_id) if t.author_id else None,
        "conversation_id": str(getattr(t, "conversation_id", "")) if getattr(t, "conversation_id", None) else None,
        "metrics": {
            "like": pm.get("like_count"),
            "reply": pm.get("reply_count"),
            "retweet": pm.get("retweet_count"),
            "quote": pm.get("quote_count"),
            "bookmark": pm.get("bookmark_count"),
            "impression": pm.get("impression_count"),
        },
        "label": label,  # <<< HIỆN TRỰC TIẾP TRONG tweets_x
        "source": "x_api_v2_search_recent",
    }


def fetch_and_save(query, batches=1, batch_size=10):
    next_token = None

    for i in range(batches):
        resp = client.search_recent_tweets(
            query=query,
            max_results=batch_size,
            next_token=next_token,
            tweet_fields=[
                "created_at",
                "lang",
                "public_metrics",
                "author_id",
                "conversation_id",
            ],
        )

        tweets = resp.data or []
        meta = resp.meta or {}
        next_token = meta.get("next_token")

        print(f"[Batch {i+1}] fetched={len(tweets)}")

        for t in tweets:
            try:
                col.insert_one(to_doc(t))
            except DuplicateKeyError:
                pass

        if not next_token:
            break

        time.sleep(1.2)

if __name__ == "__main__":
    query = "kafka lang:en -is:retweet"
    fetch_and_save(query)
