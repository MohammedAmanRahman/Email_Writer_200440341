from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Category, Complaint
from .serializers import (
    CategorySerializer,
    ComplaintCreateSerializer,
    ComplaintSerializer,
)


class ComplaintViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet for listing, retrieving, and creating complaints."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return ComplaintCreateSerializer
        return ComplaintSerializer

    def get_queryset(self):
        return Complaint.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        complaint = serializer.save(user=self.request.user)

        # Run ML analysis pipeline
        try:
            from ml.predictor import analyze_complaint

            results = analyze_complaint(complaint)
            if results:
                if results.get("category"):
                    complaint.predicted_category = results["category"]
                if results.get("category_confidence") is not None:
                    complaint.category_confidence = results["category_confidence"]
                if results.get("sentiment"):
                    complaint.sentiment_label = results["sentiment"]
                if results.get("sentiment_score") is not None:
                    complaint.sentiment_score = results["sentiment_score"]
                if results.get("urgency"):
                    complaint.urgency_level = results["urgency"]
                if results.get("entities"):
                    complaint.entities = results["entities"]
                    if not complaint.company_name and results["entities"].get("company"):
                        complaint.company_name = results["entities"]["company"]
                    if not complaint.product and results["entities"].get("product"):
                        complaint.product = results["entities"]["product"]
                    if results["entities"].get("timeframe"):
                        complaint.timeframe = results["entities"]["timeframe"]
                if results.get("matched_strategy"):
                    complaint.matched_strategy = results["matched_strategy"]
                complaint.save()
        except ImportError:
            pass

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return full representation
        complaint = Complaint.objects.get(pk=serializer.instance.pk)
        output_serializer = ComplaintSerializer(complaint)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class CategoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only ViewSet for complaint categories."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """Return aggregate complaint statistics as JSON for dashboards."""
    # Complaints by category
    category_counts = (
        Complaint.objects.filter(predicted_category__isnull=False)
        .values("predicted_category__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Sentiment distribution
    sentiment_counts = (
        Complaint.objects.exclude(sentiment_label="")
        .values("sentiment_label")
        .annotate(count=Count("id"))
        .order_by("sentiment_label")
    )

    # Urgency distribution
    urgency_counts = (
        Complaint.objects.exclude(urgency_level="")
        .values("urgency_level")
        .annotate(count=Count("id"))
        .order_by("urgency_level")
    )

    # Trends over the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    trend_data = (
        Complaint.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    data = {
        "categories": {
            "labels": [c["predicted_category__name"] for c in category_counts],
            "data": [c["count"] for c in category_counts],
        },
        "sentiment": {
            "labels": [s["sentiment_label"] for s in sentiment_counts],
            "data": [s["count"] for s in sentiment_counts],
        },
        "urgency": {
            "labels": [u["urgency_level"] for u in urgency_counts],
            "data": [u["count"] for u in urgency_counts],
        },
        "trends": {
            "labels": [t["date"].isoformat() for t in trend_data],
            "data": [t["count"] for t in trend_data],
        },
    }

    return Response(data)
