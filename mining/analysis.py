"""
Complaint Pattern Analysis - Data Mining Module
Analyses patterns in complaint data: trends, distributions, correlations.
"""
import pandas as pd
import numpy as np
from collections import Counter
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncMonth, TruncWeek


class ComplaintAnalyzer:
    """Analyses complaint data for patterns and trends."""

    def get_category_distribution(self):
        """Count complaints per category."""
        from complaints.models import Complaint
        return list(
            Complaint.objects.filter(predicted_category__isnull=False)
            .values("predicted_category__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

    def get_sentiment_distribution(self):
        """Distribution of sentiment labels."""
        from complaints.models import Complaint
        return list(
            Complaint.objects.exclude(sentiment_label="")
            .values("sentiment_label")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

    def get_urgency_distribution(self):
        """Distribution of urgency levels."""
        from complaints.models import Complaint
        return list(
            Complaint.objects.exclude(urgency_level="")
            .values("urgency_level")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

    def get_monthly_trends(self):
        """Complaint counts grouped by month."""
        from complaints.models import Complaint
        return list(
            Complaint.objects
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

    def get_company_stats(self):
        """Top companies by complaint count with avg sentiment."""
        from complaints.models import Complaint
        return list(
            Complaint.objects.exclude(company_name="")
            .values("company_name")
            .annotate(
                count=Count("id"),
                avg_sentiment=Avg("sentiment_score"),
            )
            .order_by("-count")[:20]
        )

    def get_category_sentiment_cross(self):
        """Cross-tabulation of category vs sentiment."""
        from complaints.models import Complaint
        return list(
            Complaint.objects.filter(
                predicted_category__isnull=False
            ).exclude(sentiment_label="")
            .values("predicted_category__name", "sentiment_label")
            .annotate(count=Count("id"))
        )

    def get_resolution_rates(self):
        """Resolution/response rates from CFPB data."""
        from complaints.models import CFPBComplaint
        total = CFPBComplaint.objects.count()
        if total == 0:
            return {}
        timely = CFPBComplaint.objects.filter(timely_response=True).count()
        disputed = CFPBComplaint.objects.filter(consumer_disputed=True).count()
        return {
            "total": total,
            "timely_response_rate": round(timely / total, 4) if total else 0,
            "dispute_rate": round(disputed / total, 4) if total else 0,
            "response_types": list(
                CFPBComplaint.objects.values("company_response")
                .annotate(count=Count("id"))
                .order_by("-count")[:10]
            ),
        }

    def get_keyword_analysis(self, top_n=30):
        """Most common words in complaints (excluding stopwords)."""
        from complaints.models import Complaint
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "was", "are", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "can", "shall",
            "i", "me", "my", "we", "our", "you", "your", "they", "them",
            "their", "it", "its", "this", "that", "these", "those", "not",
            "no", "so", "if", "then", "than", "too", "very", "just",
        }
        texts = Complaint.objects.values_list("raw_text", flat=True)
        word_counts = Counter()
        for text in texts:
            words = text.lower().split()
            words = [''.join(c for c in w if c.isalnum()) for w in words]
            word_counts.update(w for w in words if w and w not in stopwords and len(w) > 2)
        return word_counts.most_common(top_n)

    def get_full_dashboard_data(self):
        """Compile all analysis data for the dashboard."""
        return {
            "category_distribution": self.get_category_distribution(),
            "sentiment_distribution": self.get_sentiment_distribution(),
            "urgency_distribution": self.get_urgency_distribution(),
            "monthly_trends": self.get_monthly_trends(),
            "company_stats": self.get_company_stats(),
            "category_sentiment": self.get_category_sentiment_cross(),
            "resolution_rates": self.get_resolution_rates(),
            "top_keywords": self.get_keyword_analysis(),
        }
