from django.shortcuts import render
from django.http import JsonResponse
from .services import (
    get_kpis, get_sentiment_series, get_latest_tweets, get_sources
)

def index(request):
    return render(request, "dashboard/index.html")

def api_overview(request):
    last_minutes = int(request.GET.get("minutes", "60"))
    return JsonResponse({
        "kpis": get_kpis(last_minutes=last_minutes),
        "sources": get_sources(),
    }, safe=True)

def api_series(request):
    limit = int(request.GET.get("limit", "120"))
    return JsonResponse(get_sentiment_series(limit=limit), safe=False)

def api_latest(request):
    label = request.GET.get("label", "all")
    source = request.GET.get("source", "all")
    limit = int(request.GET.get("limit", "20"))
    return JsonResponse(get_latest_tweets(limit=limit, label=label, source=source), safe=False)
