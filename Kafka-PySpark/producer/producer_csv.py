import os
import csv
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from kafka import KafkaProducer

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "tweets_raw")
CSV_PATH = os.getenv("CSV_PATH", "twitter.csv")

TEXT_INDEX = int(os.getenv("CSV_TEXT_INDEX", "5"))
ID_INDEX = int(os.getenv("CSV_ID_INDEX", "1"))
DATE_INDEX = int(os.getenv("CSV_DATE_INDEX", "2"))
USER_INDEX = int(os.getenv("CSV_USER_INDEX", "4"))
LABEL_INDEX = int(os.getenv("CSV_LABEL_INDEX", "0"))

SLEEP_SEC = float(os.getenv("CSV_SLEEP_SEC", "0.1"))
FLUSH_EVERY = int(os.getenv("CSV_FLUSH_EVERY", "50"))

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    api_version=(2, 8, 0),
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
)


def _maybe_parse_twitter_date(s: str) -> str:
 
    now = datetime.now(timezone.utc).isoformat()
    if not s:
        return now

  
    candidates = [
        "%a %b %d %H:%M:%S %Z %Y",
        "%a %b %d %H:%M:%S %Y",
    ]

    for fmt in candidates:
        try:
            dt = datetime.strptime(s.strip(), fmt)
        
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass

    return now

def _looks_like_header(row: list) -> bool:

    if not row:
        return False
    joined = ",".join([c.strip().lower() for c in row])
    return ("sentiment" in joined and "text" in joined) or (row[0].strip().lower() == "sentiment")

def row_to_msg(row: list, idx: int) -> dict:

    if not row:
        return {}

    # Lấy text đúng cột
    text = row[TEXT_INDEX].strip() if len(row) > TEXT_INDEX else ""
    if not text:
        return {}

    tweet_id = ""
    if len(row) > ID_INDEX:
        tweet_id = str(row[ID_INDEX]).strip()
    if not tweet_id:
        tweet_id = f"csv_{idx}"

    created_at_raw = row[DATE_INDEX].strip() if len(row) > DATE_INDEX else ""
    created_at = _maybe_parse_twitter_date(created_at_raw)

    username = row[USER_INDEX].strip() if len(row) > USER_INDEX else None
    label = row[LABEL_INDEX].strip() if len(row) > LABEL_INDEX else None

    return {
        "tweet_id": tweet_id,
        "text": text,
        "created_at": created_at,
        "lang": "en",  
        "author_id": username, 
        "conversation_id": None,
        "public_metrics": {
            "like": None,
            "reply": None,
            "retweet": None,
            "quote": None,
            "bookmark": None,
            "impression": None,
        },
        "source": "csv_kaggle",
        "csv_meta": {
            "label": label,
            "username": username,
            "raw_date": created_at_raw,
        }
    }

def main():
    print(f"[CSV Producer] bootstrap={KAFKA_BOOTSTRAP} topic={TOPIC} file={CSV_PATH}")
    print(f"[CSV Mapping] text_idx={TEXT_INDEX} id_idx={ID_INDEX} date_idx={DATE_INDEX} user_idx={USER_INDEX}")

    sent = 0
    skipped = 0

    with open(CSV_PATH, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)

        first = True
        for idx, row in enumerate(reader, 1):
            if first:
                first = False
                if _looks_like_header(row):
                    print("[CSV Producer] Detected header row -> skipped")
                    skipped += 1
                    continue

            msg = row_to_msg(row, idx)
            if not msg:
                skipped += 1
                continue

            producer.send(TOPIC, msg)
            sent += 1

            if sent % FLUSH_EVERY == 0:
                producer.flush()
                print(f"Sent {sent} messages... (skipped={skipped})")

            time.sleep(SLEEP_SEC)

    producer.flush()
    print(f"Done. sent={sent} skipped={skipped}")

if __name__ == "__main__":
    main()
