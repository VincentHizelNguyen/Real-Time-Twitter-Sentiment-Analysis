import os
import json
import time
from dotenv import load_dotenv
import tweepy
from kafka import KafkaProducer

load_dotenv()

BEARER = os.getenv("X_BEARER_TOKEN")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "tweets_raw")

if not BEARER:
    raise RuntimeError("Missing X_BEARER_TOKEN in .env")

client = tweepy.Client(bearer_token=BEARER, wait_on_rate_limit=True)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
)

def tweet_to_msg(t) -> dict:
    pm = t.public_metrics or {}
    return {
        "tweet_id": str(t.id),
        "text": t.text,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "lang": t.lang,
        "author_id": str(t.author_id) if t.author_id else None,
        "conversation_id": str(getattr(t, "conversation_id", "")) if getattr(t, "conversation_id", None) else None,
        "public_metrics": {
            "like": pm.get("like_count"),
            "reply": pm.get("reply_count"),
            "retweet": pm.get("retweet_count"),
            "quote": pm.get("quote_count"),
            "bookmark": pm.get("bookmark_count"),
            "impression": pm.get("impression_count"),
        },
        "source": "x_api_v2_search_recent",
    }

def run(query: str, poll_seconds: float = 2.0, batch_size: int = 10):
    next_token = None
    print(f"Producer started. topic={TOPIC} bootstrap={KAFKA_BOOTSTRAP}")
    print(f"Query: {query}")

    while True:
        resp = client.search_recent_tweets(
            query=query,
            max_results=batch_size,
            next_token=next_token,
            tweet_fields=["created_at", "lang", "public_metrics", "author_id", "conversation_id"],
        )

        tweets = resp.data or []
        meta = resp.meta or {}
        next_token = meta.get("next_token")

        print(f"Fetched={len(tweets)} next_token={'yes' if next_token else 'no'}")

        for t in tweets:
            msg = tweet_to_msg(t)
            producer.send(TOPIC, msg)

        producer.flush()


        time.sleep(poll_seconds)
        if not next_token:
            next_token = None

if __name__ == "__main__":
    # bạn đổi query tuỳ ý
    query = "kafka lang:en -is:retweet"
    run(query=query)
