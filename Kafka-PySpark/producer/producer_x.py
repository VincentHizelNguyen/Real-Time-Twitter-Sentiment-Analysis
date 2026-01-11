import os
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
import tweepy
from kafka import KafkaProducer

load_dotenv()

BEARER = os.getenv("X_BEARER_TOKEN")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "tweets_raw")
QUERY = os.getenv("X_QUERY", "kafka lang:en -is:retweet")

POLL_SECONDS = float(os.getenv("X_POLL_SECONDS", "2.0"))
BATCH_SIZE = int(os.getenv("X_BATCH_SIZE", "10"))

if not BEARER:
    raise RuntimeError("Missing X_BEARER_TOKEN in .env")

client = tweepy.Client(bearer_token=BEARER, wait_on_rate_limit=True)

# ✅ BỎ api_version để client tự negotiate với broker (đỡ lỗi đổi version)
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
)

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def tweet_to_msg(t) -> dict:
    pm = t.public_metrics or {}

    # ✅ created_at không được None -> fallback now UTC để Spark parse event_time
    created_at = t.created_at.isoformat() if getattr(t, "created_at", None) else _utc_now_iso()

    return {
        "tweet_id": str(t.id),
        "text": t.text,
        "created_at": created_at,
        "lang": getattr(t, "lang", None),
        "author_id": str(t.author_id) if getattr(t, "author_id", None) else None,
        "conversation_id": str(getattr(t, "conversation_id")) if getattr(t, "conversation_id", None) else None,
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

def run(poll_seconds: float = POLL_SECONDS, batch_size: int = BATCH_SIZE):
    next_token = None

    # ✅ since_id kiểu truyền thống: chỉ lấy tweet mới hơn (giảm trùng + sạch dữ liệu)
    # Lưu trong RAM; muốn bền qua restart thì ghi ra file.
    last_seen_id = None

    print(f"[X Producer] bootstrap={KAFKA_BOOTSTRAP} topic={TOPIC}")
    print(f"Query: {QUERY}")
    print(f"poll_seconds={poll_seconds} batch_size={batch_size}")

    sent = 0
    skipped = 0

    while True:
        try:
            # Một số version Tweepy/support có since_id, một số không.
            # Tao thử dùng since_id trước; nếu lỗi thì fallback cách filter id.
            kwargs = dict(
                query=QUERY,
                max_results=batch_size,
                next_token=next_token,
                tweet_fields=["created_at", "lang", "public_metrics", "author_id", "conversation_id"],
            )
            if last_seen_id is not None:
                kwargs["since_id"] = last_seen_id  # nếu API không support sẽ throw TypeError/HTTP error

            resp = client.search_recent_tweets(**kwargs)

        except TypeError:
            # ✅ Fallback: Tweepy version không nhận since_id param
            resp = client.search_recent_tweets(
                query=QUERY,
                max_results=batch_size,
                next_token=next_token,
                tweet_fields=["created_at", "lang", "public_metrics", "author_id", "conversation_id"],
            )

        tweets = resp.data or []
        meta = resp.meta or {}
        next_token = meta.get("next_token")

        # Nếu không dùng since_id được: filter thủ công theo last_seen_id (string compare id là OK vì tweet id tăng dần)
        for t in tweets:
            tid = str(t.id)

            if last_seen_id is not None:
                try:
                    if int(tid) <= int(last_seen_id):
                        skipped += 1
                        continue
                except Exception:
                    # nếu lỡ parse int fail thì bỏ qua filter
                    pass

            producer.send(TOPIC, tweet_to_msg(t))
            sent += 1

            # cập nhật last_seen_id = max
            if last_seen_id is None:
                last_seen_id = tid
            else:
                try:
                    if int(tid) > int(last_seen_id):
                        last_seen_id = tid
                except Exception:
                    last_seen_id = tid

        producer.flush()

        if sent % 50 == 0 and sent > 0:
            print(f"Sent={sent} skipped={skipped} last_seen_id={last_seen_id}")

        time.sleep(poll_seconds)

        # Hết trang thì quay lại poll từ đầu
        if not next_token:
            next_token = None

if __name__ == "__main__":
    run()
