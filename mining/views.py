"""
Mining Dashboard Views - Data Mining Module
Provides views for the data mining dashboard, association rules, and clustering.
"""
import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .analysis import ComplaintAnalyzer
from .association import AssociationMiner
from .clustering import ComplaintClusterer

logger = logging.getLogger(__name__)


def _serialize_value(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "item"):
        # numpy scalar
        return obj.item()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@login_required
def dashboard(request):
    """Render the data mining dashboard with analysis data."""
    analyzer = ComplaintAnalyzer()
    try:
        data = analyzer.get_full_dashboard_data()
    except Exception as e:
        logger.error("Error generating dashboard data: %s", e)
        data = {"error": str(e)}

    # Serialize monthly trends for the template (dates need conversion)
    if "monthly_trends" in data:
        for item in data["monthly_trends"]:
            if "month" in item and isinstance(item["month"], datetime):
                item["month"] = item["month"].isoformat()

    context = {
        "dashboard_data": data,
        "dashboard_json": json.dumps(data, default=_serialize_value),
    }
    return render(request, "mining/dashboard.html", context)


@login_required
def dashboard_api(request):
    """Return JSON of all analysis data for AJAX calls."""
    analyzer = ComplaintAnalyzer()
    try:
        data = analyzer.get_full_dashboard_data()
    except Exception as e:
        logger.error("Error generating dashboard API data: %s", e)
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(data, safe=False, json_dumps_params={
        "default": _serialize_value,
    })


@login_required
def association_rules(request):
    """Return page or JSON of discovered association rules."""
    miner = AssociationMiner()

    min_support = float(request.GET.get("min_support", 0.05))
    min_confidence = float(request.GET.get("min_confidence", 0.5))

    try:
        miner.prepare_transactions()
        miner.find_rules(min_support=min_support, min_confidence=min_confidence)
        rules = miner.format_rules()
        strategy_assocs = miner.get_strategy_associations()
    except Exception as e:
        logger.error("Error generating association rules: %s", e)
        rules = []
        strategy_assocs = []

    data = {
        "rules": rules,
        "strategy_associations": strategy_assocs,
        "params": {
            "min_support": min_support,
            "min_confidence": min_confidence,
        },
        "transaction_count": len(miner.transactions),
    }

    if request.headers.get("Accept") == "application/json" or request.GET.get("format") == "json":
        return JsonResponse(data, safe=False)

    context = {
        "data": data,
        "data_json": json.dumps(data, default=_serialize_value),
    }
    return render(request, "mining/associations.html", context)


@login_required
def cluster_view(request):
    """Return page or JSON of cluster analysis."""
    n_clusters = int(request.GET.get("n_clusters", 5))

    clusterer = ComplaintClusterer()
    try:
        success = clusterer.fit(n_clusters=n_clusters)
        if success:
            summaries = clusterer.get_cluster_summaries()
            outliers = clusterer.get_outliers()
        else:
            summaries = []
            outliers = []
    except Exception as e:
        logger.error("Error generating cluster analysis: %s", e)
        summaries = []
        outliers = []

    data = {
        "n_clusters": n_clusters,
        "cluster_summaries": summaries,
        "outliers": outliers[:20],  # Limit outliers to top 20
    }

    if request.headers.get("Accept") == "application/json" or request.GET.get("format") == "json":
        return JsonResponse(data, safe=False, json_dumps_params={
            "default": _serialize_value,
        })

    context = {
        "data": data,
        "data_json": json.dumps(data, default=_serialize_value),
    }
    return render(request, "mining/clusters.html", context)
