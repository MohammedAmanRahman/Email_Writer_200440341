from django import forms
from django.db import models

from .models import Category, Complaint, ExampleLetter


PRODUCT_CHOICES = [
    ("", "-- Select a product/service --"),
    ("Common", (
        ("Broadband", "Broadband"),
        ("Mobile Phone", "Mobile Phone"),
        ("Credit Card", "Credit Card"),
        ("Bank Account", "Bank Account"),
        ("Energy Supply", "Energy Supply"),
        ("Water Supply", "Water Supply"),
        ("Insurance", "Insurance"),
        ("Mortgage", "Mortgage"),
        ("Loan", "Loan"),
    )),
    ("Telecoms", (
        ("Home Phone", "Home Phone"),
        ("WiFi", "WiFi"),
        ("TV Package", "TV Package"),
        ("SIM Contract", "SIM Contract"),
    )),
    ("Retail", (
        ("Online Order", "Online Order"),
        ("In-Store Purchase", "In-Store Purchase"),
        ("Warranty Claim", "Warranty Claim"),
        ("Subscription", "Subscription"),
    )),
    ("Transport", (
        ("Train Journey", "Train Journey"),
        ("Flight", "Flight"),
        ("Bus Service", "Bus Service"),
        ("Taxi/Rideshare", "Taxi/Rideshare"),
    )),
    ("Property", (
        ("Rental Property", "Rental Property"),
        ("Plumbing", "Plumbing"),
        ("Heating", "Heating"),
        ("Building Work", "Building Work"),
    )),
    ("Other", (
        ("Other", "Other (type below)"),
    )),
]

# Map product choices to categories for auto-classification
PRODUCT_TO_CATEGORY = {
    "Broadband": "Telecoms",
    "Mobile Phone": "Telecoms",
    "Home Phone": "Telecoms",
    "WiFi": "Telecoms",
    "TV Package": "Telecoms",
    "SIM Contract": "Telecoms",
    "Credit Card": "Financial Services",
    "Bank Account": "Financial Services",
    "Insurance": "Financial Services",
    "Mortgage": "Financial Services",
    "Loan": "Financial Services",
    "Energy Supply": "Utilities",
    "Water Supply": "Utilities",
    "Online Order": "Retail",
    "In-Store Purchase": "Retail",
    "Warranty Claim": "Retail",
    "Subscription": "Retail",
    "Train Journey": "Transport",
    "Flight": "Transport",
    "Bus Service": "Transport",
    "Taxi/Rideshare": "Transport",
    "Rental Property": "Property",
    "Plumbing": "Property",
    "Heating": "Property",
    "Building Work": "Property",
}


class ComplaintForm(forms.ModelForm):
    company_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Company name (optional)",
            }
        ),
    )
    product = forms.ChoiceField(
        choices=PRODUCT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    custom_product = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Type your own product/service...",
            }
        ),
    )

    class Meta:
        model = Complaint
        fields = ["raw_text", "company_name"]
        widgets = {
            "raw_text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Describe your complaint in detail...",
                    "rows": 6,
                }
            ),
        }

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product", "")
        custom = cleaned.get("custom_product", "").strip()

        if custom:
            cleaned["product"] = custom
        elif product == "Other":
            cleaned["product"] = custom or ""

        return cleaned


class ExampleLetterForm(forms.Form):
    """Form for pasting a complaint letter — the system extracts the rest."""
    product = forms.ChoiceField(
        choices=PRODUCT_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="What product/service does this letter relate to?",
    )
    custom_product = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Type your own product/service...",
        }),
        help_text="Type a new product/service if none of the above fit.",
    )
    company_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. BT, Sky, Currys, British Gas...",
        }),
        help_text="The company this letter is about. Leave blank to auto-detect.",
    )
    letter_text = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Paste the full complaint letter here...",
            "rows": 14,
        }),
        help_text="Paste a real complaint letter. The system will extract companies, products, issues, and keywords automatically.",
    )

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product", "")
        custom = cleaned.get("custom_product", "").strip()

        if not product and not custom:
            raise forms.ValidationError(
                "Please select a product/service or type your own."
            )

        if custom:
            cleaned["product"] = custom
        elif product == "Other":
            cleaned["product"] = custom or ""

        # Resolve category from product
        final_product = cleaned["product"]
        category_name = PRODUCT_TO_CATEGORY.get(final_product, "")

        if category_name:
            cat, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={"description": f"{category_name} complaints"},
            )
        else:
            # Use the product group name or create a general one
            cat, _ = Category.objects.get_or_create(
                name="General",
                defaults={"description": "General complaints"},
            )

        cleaned["category"] = cat
        return cleaned
