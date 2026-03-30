from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    complaint_count = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Complaint(models.Model):
    URGENCY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    SENTIMENT_CHOICES = [
        ("positive", "Positive"),
        ("neutral", "Neutral"),
        ("negative", "Negative"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaints",
    )
    raw_text = models.TextField(help_text="Original complaint text")
    encrypted_personal_data = models.BinaryField(
        null=True, blank=True, editable=False
    )

    # ML classification results
    predicted_category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="complaints",
    )
    category_confidence = models.FloatField(null=True, blank=True)
    sentiment_label = models.CharField(
        max_length=20, choices=SENTIMENT_CHOICES, blank=True
    )
    sentiment_score = models.FloatField(null=True, blank=True)
    urgency_level = models.CharField(
        max_length=20, choices=URGENCY_CHOICES, blank=True
    )

    # NER results
    entities = models.JSONField(default=dict, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    product = models.CharField(max_length=200, blank=True)
    timeframe = models.CharField(max_length=200, blank=True)

    # Strategy matching
    matched_strategy = models.ForeignKey(
        "ComplaintStrategy", null=True, blank=True, on_delete=models.SET_NULL
    )

    # Status & letter storage
    letter_generated = models.BooleanField(default=False)
    letter_file = models.FileField(upload_to="letters/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Complaint #{self.pk} by {self.user.username}"

    def encrypt_personal_data(self, data: str) -> None:
        key = (
            settings.ENCRYPTION_KEY.encode()
            if isinstance(settings.ENCRYPTION_KEY, str)
            else settings.ENCRYPTION_KEY
        )
        try:
            f = Fernet(key)
            self.encrypted_personal_data = f.encrypt(data.encode())
        except Exception:
            # If encryption key is invalid (dev default), store as-is encoded
            self.encrypted_personal_data = data.encode()

    def decrypt_personal_data(self) -> str:
        if not self.encrypted_personal_data:
            return ""
        data = bytes(self.encrypted_personal_data)
        key = (
            settings.ENCRYPTION_KEY.encode()
            if isinstance(settings.ENCRYPTION_KEY, str)
            else settings.ENCRYPTION_KEY
        )
        try:
            f = Fernet(key)
            return f.decrypt(data).decode()
        except Exception:
            return data.decode()


class ComplaintStrategy(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="strategies"
    )
    title = models.CharField(max_length=200)
    strategy_text = models.TextField()
    success_rate = models.FloatField(default=0.0)
    letter_template = models.TextField(
        help_text=(
            "Template for complaint letter. Use {company}, {product}, "
            "{complaint_summary}, {timeframe}, {user_name}, {date} as "
            "placeholders."
        )
    )
    times_used = models.IntegerField(default=0)

    class Meta:
        ordering = ["-success_rate"]

    def __str__(self):
        return f"{self.title} ({self.success_rate:.0%})"


class ExampleLetter(models.Model):
    """
    Real complaint letters used as training examples.
    The system finds the best matching example and adapts it for new complaints.
    """
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="example_letters"
    )
    company_type = models.CharField(
        max_length=100,
        help_text="Type of company e.g. 'ISP', 'Bank', 'Energy', 'Retailer', 'Airline'",
    )
    issue_type = models.CharField(
        max_length=200,
        help_text="e.g. 'Service outage', 'Billing error', 'Faulty product', 'Delayed refund'",
    )
    keywords = models.TextField(
        blank=True,
        help_text="Comma-separated keywords for matching e.g. 'broadband,wifi,internet,outage'",
    )
    letter_body = models.TextField(
        help_text="The full complaint letter body. Use {company}, {product}, {timeframe}, {user_name}, {date} as placeholders for personalisation.",
    )
    source = models.CharField(
        max_length=200,
        blank=True,
        help_text="Where this letter came from e.g. 'Citizens Advice template', 'User provided'",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "issue_type"]

    def __str__(self):
        return f"{self.category.name} - {self.issue_type} ({self.company_type})"

    def keyword_list(self):
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]


class CFPBComplaint(models.Model):
    """Raw CFPB complaint data for training and data mining."""

    date_received = models.DateField(null=True, blank=True)
    product = models.CharField(max_length=200)
    sub_product = models.CharField(max_length=200, blank=True)
    issue = models.CharField(max_length=300, blank=True)
    sub_issue = models.CharField(max_length=300, blank=True)
    complaint_narrative = models.TextField(blank=True)
    company = models.CharField(max_length=200)
    state = models.CharField(max_length=10, blank=True)
    submitted_via = models.CharField(max_length=50, blank=True)
    company_response = models.CharField(max_length=200, blank=True)
    timely_response = models.BooleanField(default=False)
    consumer_disputed = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "CFPB Complaint"
        verbose_name_plural = "CFPB Complaints"

    def __str__(self):
        return f"{self.product} - {self.company}"
