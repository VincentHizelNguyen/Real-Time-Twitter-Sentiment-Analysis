from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from django.conf import settings

client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

RAW_COL = "tweets_labeled"
AGG_COL = "sentiment_agg"

def _dt(v):
    # Mongo có thể lưu datetime hoặc string -> cố gắng normalize
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            # ISO8601
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    return None

def get_kpis(last_minutes=60):
    col = db[RAW_COL]
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=last_minutes)

    # event_time trong pipeline là timestamp -> thường là datetime trong Mongo connector
    total = col.estimated_document_count()

    recent = col.count_documents({"event_time": {"$gte": since}})
    by_label = list(col.aggregate([
        {"$match": {"event_time": {"$gte": since}}},
        {"$group": {"_id": "$label", "cnt": {"$sum": 1}}},
    ]))

    by_source = list(col.aggregate([
        {"$match": {"event_time": {"$gte": since}}},
        {"$group": {"_id": "$source", "cnt": {"$sum": 1}}},
        {"$sort": {"cnt": -1}},
        {"$limit": 10},
    ]))

    by_region = list(col.aggregate([
        {"$match": {"event_time": {"$gte": since}}},
        {"$group": {"_id": "$region", "cnt": {"$sum": 1}}},
        {"$sort": {"cnt": -1}},
    ]))

    label_map = {x["_id"] or "unknown": x["cnt"] for x in by_label}
    return {
        "total_docs": total,
        "recent_docs": recent,
        "last_minutes": last_minutes,
        "labels": {
            "positive": label_map.get("positive", 0),
            "negative": label_map.get("negative", 0),
            "neutral": label_map.get("neutral", 0),
            "unknown": label_map.get("unknown", 0),
        },
        "by_source": [{"name": x["_id"] or "unknown", "cnt": x["cnt"]} for x in by_source],
        "by_region": [{"name": x["_id"] or "unknown", "cnt": x["cnt"]} for x in by_region],
    }

def get_sentiment_series(limit=120):
    # lấy từ sentiment_agg (window_start/end + counts)
    col = db[AGG_COL]
    cur = col.find({}, {"_id": 0}).sort("window_start", -1).limit(limit)
    rows = list(cur)
    rows.reverse()  # để chart đi từ cũ -> mới

    # normalize
    out = []
    for r in rows:
        ws = r.get("window_start")
        we = r.get("window_end")
        ws_dt = _dt(ws)
        we_dt = _dt(we)

        out.append({
            "window_start": (ws_dt.isoformat() if ws_dt else str(ws)),
            "window_end": (we_dt.isoformat() if we_dt else str(we)),
            "region": r.get("region", "unknown"),
            "source": r.get("source", "unknown"),
            "positive": int(r.get("positive", 0) or 0),
            "negative": int(r.get("negative", 0) or 0),
            "neutral": int(r.get("neutral", 0) or 0),
        })
    return out

def get_latest_tweets(limit=20, label=None, source=None):
    col = db[RAW_COL]
    q = {}
    if label and label != "all":
        q["label"] = label
    if source and source != "all":
        q["source"] = source

    cur = col.find(q, {
        "_id": 0,
        "tweet_id": 1, "text": 1, "created_at": 1, "event_time": 1,
        "label": 1, "source": 1, "region": 1, "author_id": 1
    }).sort("event_time", -1).limit(limit)

    rows = list(cur)
    # normalize time fields
    out = []
    for r in rows:
        et = _dt(r.get("event_time"))
        out.append({
            "tweet_id": r.get("tweet_id"),
            "text": r.get("text", ""),
            "label": r.get("label", "unknown"),
            "source": r.get("source", "unknown"),
            "region": r.get("region", "unknown"),
            "author_id": r.get("author_id"),
            "event_time": et.isoformat() if et else str(r.get("event_time")),
        })
    return out

def get_sources():
    col = db[RAW_COL]
    vals = col.distinct("source")
    vals = [v for v in vals if v]
    vals.sort()
    return vals
