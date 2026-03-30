from django.contrib import admin

from .models import Category, CFPBComplaint, Complaint, ComplaintStrategy, ExampleLetter


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "complaint_count")
    search_fields = ("name",)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "user",
        "predicted_category",
        "sentiment_label",
        "urgency_level",
        "letter_generated",
        "created_at",
    )
    list_filter = (
        "predicted_category",
        "sentiment_label",
        "urgency_level",
        "letter_generated",
        "created_at",
    )
    search_fields = ("raw_text", "company_name", "product", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ComplaintStrategy)
class ComplaintStrategyAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "success_rate", "times_used")
    list_filter = ("category",)
    search_fields = ("title", "strategy_text")


@admin.register(ExampleLetter)
class ExampleLetterAdmin(admin.ModelAdmin):
    list_display = ("category", "company_type", "issue_type", "source", "created_at")
    list_filter = ("category", "company_type")
    search_fields = ("issue_type", "keywords", "letter_body", "company_type")


@admin.register(CFPBComplaint)
class CFPBComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "company",
        "issue",
        "date_received",
        "timely_response",
    )
    list_filter = ("product", "timely_response", "consumer_disputed")
    search_fields = ("complaint_narrative", "company", "product", "issue")
