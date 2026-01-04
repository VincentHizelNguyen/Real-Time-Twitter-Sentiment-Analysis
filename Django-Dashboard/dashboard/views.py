from datetime import datetime, timedelta
from dateutil import tz
from django.conf import settings
from django.shortcuts import render
from pymongo import MongoClient, DESCENDING

# ---------- Helpers ----------
def _get_mongo():
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    col = db[settings.MONGO_COL]
    return client, col
def _sentiment_counts(col):
    total = col.count_documents({})

    # field label của mày là prediction, giá trị "Positive/Negative/Neutral"
    #pos = col.count_documents({"prediction": {"$regex": r"^positive$", "$options": "i"}})
    #neg = col.count_documents({"prediction": {"$regex": r"^negative$", "$options": "i"}})
    #neu = col.count_documents({"prediction": {"$regex": r"^neutral$",  "$options": "i"}})

    pos = col.count_documents({"label": {"$regex": r"^positive$", "$options": "i"}})
    neg = col.count_documents({"label": {"$regex": r"^negative$", "$options": "i"}})
    neu = col.count_documents({"label": {"$regex": r"^neutral$",  "$options": "i"}})

    known = pos + neg + neu
    other = max(total - known, 0)
    return total, pos, neg, neu, other

'''
def _get_latest_tweets(col, limit=20):
    cursor = col.find(
        {},
        {
            "_id": 0,
            "tweet": 1,
            "clean_tweet": 1,
            "prediction": 1,
            "source": 1,
            "model": 1,
            "created_at": 1,
        }
    ).sort([("_id", -1)]).limit(limit)

    latest = []
    for doc in cursor:
        latest.append({
            "username": doc.get("source", "-"),     # kafka
            "text": doc.get("clean_tweet") or doc.get("tweet") or "",
       
            "sentiment": doc.get("prediction", "unknown"),
            "created_at": doc.get("created_at", "-"),
        })

    return latest
'''
def _get_latest_tweets(col, limit=20):
    cursor = col.find({}, {"_id":0, "text":1, "label":1, "created_at":1, "source":1}) \
                .sort([("_id",-1)]).limit(limit)

    latest = []
    for doc in cursor:
        latest.append({
            "username": doc.get("source", "-"),
            "text": (doc.get("text") or "")[:500],
            "sentiment": doc.get("label", "unknown"),
            "created_at": doc.get("created_at", "-"),
        })
    return latest



def _series_by_day(col, days=14):

    end = datetime.now()
    start = end - timedelta(days=days - 1)

    pipeline = [
        {"$match": {"created_at": {"$gte": start, "$lte": end}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]

    raw = list(col.aggregate(pipeline))
    raw_map = {x["_id"]: x["count"] for x in raw}

    labels = []
    values = []
    for i in range(days):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(d)
        values.append(raw_map.get(d, 0))

    return labels, values

# ---------- Main View ----------
def dashboard_view(request):
    client, col = _get_mongo()
    try:
        total, pos, neg, neu, other = _sentiment_counts(col)


        # Nếu created_at không phải datetime thì line chart sẽ fail.
        # Tao vẫn try, fail thì trả series rỗng cho khỏi chết trang.
        try:
            day_labels, day_counts = _series_by_day(col, days=14)
        except Exception:
            day_labels, day_counts = [], []

        latest = _get_latest_tweets(col, limit=20)

        context = {
            "total": total,
            "pos": pos,
            "neg": neg,
            "neu": neu,
            "other": other,
            "day_labels": day_labels,
            "day_counts": day_counts,
            "latest": latest,
            "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return render(request, "dashboard/dashboard.html", context)
    finally:
        client.close()
