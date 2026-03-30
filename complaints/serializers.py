from rest_framework import serializers

from .models import Category, Complaint


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ComplaintSerializer(serializers.ModelSerializer):
    predicted_category_name = serializers.CharField(
        source="predicted_category.name", read_only=True, default=""
    )
    matched_strategy_title = serializers.CharField(
        source="matched_strategy.title", read_only=True, default=""
    )
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Complaint
        exclude = ("encrypted_personal_data",)
        read_only_fields = (
            "user",
            "predicted_category",
            "category_confidence",
            "sentiment_label",
            "sentiment_score",
            "urgency_level",
            "entities",
            "timeframe",
            "matched_strategy",
            "letter_generated",
            "created_at",
            "updated_at",
        )


class ComplaintCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ("raw_text", "company_name", "product")
