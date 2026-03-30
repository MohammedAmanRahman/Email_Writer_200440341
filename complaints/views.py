import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ComplaintForm, ExampleLetterForm
from .models import Category, CFPBComplaint, Complaint, ComplaintStrategy, ExampleLetter
from .utils import generate_complaint_letter_pdf


@login_required
def submit_complaint(request):
    """Display the complaint form (GET) or save and analyse a complaint (POST)."""
    if request.method == "POST":
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.user = request.user
            complaint.product = form.cleaned_data.get("product", "")
            complaint.save()

            # Run ML analysis pipeline
            # The predictor handles saving all fields (category, sentiment,
            # urgency, entities, strategy) directly on the complaint object.
            try:
                from ml.predictor import analyze_complaint

                analyze_complaint(complaint)
                complaint.refresh_from_db()
            except ImportError:
                # ML module not yet available; complaint is saved without analysis
                pass

            return redirect("complaints:detail", pk=complaint.pk)
    else:
        form = ComplaintForm()

    return render(request, "complaints/submit.html", {"form": form})


@login_required
def complaint_detail(request, pk):
    """Show a single complaint with all analysis results (owner only)."""
    complaint = get_object_or_404(Complaint, pk=pk, user=request.user)
    return render(request, "complaints/detail.html", {"complaint": complaint})


@login_required
def complaint_history(request):
    """List all complaints belonging to the authenticated user."""
    complaints = Complaint.objects.filter(user=request.user)
    return render(request, "complaints/history.html", {"complaints": complaints})


@login_required
def generate_letter(request, pk):
    """Generate a PDF complaint letter, save it, and return as download."""
    complaint = get_object_or_404(Complaint, pk=pk, user=request.user)

    pdf_bytes = generate_complaint_letter_pdf(complaint)

    # Save the PDF to the complaint's letter_file field
    filename = "complaint_letter.pdf"
    complaint.letter_file.save(filename, ContentFile(pdf_bytes), save=False)
    complaint.letter_generated = True
    complaint.save(update_fields=["letter_generated", "letter_file"])

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def similar_style(request, pk):
    """Create a new complaint analysed and generated in the style of an existing one."""
    source = get_object_or_404(Complaint, pk=pk, user=request.user)

    new_text = request.POST.get("new_complaint", "").strip()
    if not new_text:
        messages.error(request, "Please enter a complaint.")
        return redirect("complaints:detail", pk=pk)

    new_company = request.POST.get("new_company", "").strip()
    new_product = request.POST.get("new_product", "").strip()

    # Create the new complaint
    new_complaint = Complaint.objects.create(
        user=request.user,
        raw_text=new_text,
        company_name=new_company,
        product=new_product,
    )

    # Run ML analysis
    try:
        from ml.predictor import analyze_complaint
        analyze_complaint(new_complaint)
        new_complaint.refresh_from_db()
    except ImportError:
        pass

    # Copy the style source's matched strategy/example letter if the new one
    # didn't find its own match
    if not new_complaint.matched_strategy and source.matched_strategy:
        new_complaint.matched_strategy = source.matched_strategy
        new_complaint.save(update_fields=["matched_strategy"])

    # Generate the letter using the source complaint's example letter as
    # the style reference. We do this by temporarily saving a high-scoring
    # ExampleLetter from the source's letter file content.
    from django.core.files.base import ContentFile
    from .utils import generate_complaint_letter_pdf, _find_best_example_letter

    # Try to find the example letter that was used for the source complaint
    # and force-match it for the new complaint
    source_example = _find_best_example_letter(source)
    if source_example:
        # Temporarily boost match by saving the source example's category
        # onto the new complaint if not already set
        if not new_complaint.predicted_category and source.predicted_category:
            new_complaint.predicted_category = source.predicted_category
            new_complaint.save(update_fields=["predicted_category"])

    # Generate PDF
    pdf_bytes = generate_complaint_letter_pdf(new_complaint)
    filename = "complaint_letter.pdf"
    new_complaint.letter_file.save(filename, ContentFile(pdf_bytes), save=False)
    new_complaint.letter_generated = True
    new_complaint.save(update_fields=["letter_generated", "letter_file"])

    # Save to training datasets
    category_name = ""
    if new_complaint.predicted_category:
        category_name = new_complaint.predicted_category.name

    # 1. CFPBComplaint record for classifier training
    CFPBComplaint.objects.create(
        product=category_name,
        sub_product=new_complaint.product,
        issue="",
        complaint_narrative=new_text,
        company=new_complaint.company_name,
        submitted_via="Similar style",
    )

    # 2. ExampleLetter record for letter generation training
    if source_example:
        ExampleLetter.objects.create(
            category=source_example.category,
            company_type=source_example.company_type,
            issue_type=source_example.issue_type,
            keywords=source_example.keywords,
            letter_body=source_example.letter_body,
            source=f"Similar style from complaint #{source.pk}",
        )

    messages.success(request, "New complaint analysed, letter generated, and added to training data.")
    return redirect("complaints:detail", pk=new_complaint.pk)


@login_required
@require_POST
def delete_complaint(request, pk):
    """Delete a complaint belonging to the authenticated user."""
    complaint = get_object_or_404(Complaint, pk=pk, user=request.user)
    # Delete stored letter file if it exists
    if complaint.letter_file:
        complaint.letter_file.delete(save=False)
    complaint.delete()
    messages.success(request, "Complaint deleted successfully.")
    return redirect("complaints:history")


@login_required
@require_POST
def delete_example(request, pk):
    """Delete an example letter."""
    example = get_object_or_404(ExampleLetter, pk=pk)
    example.delete()
    messages.success(request, "Example letter deleted.")
    return redirect("complaints:train_letters")


@login_required
def train_letters(request):
    """Page to paste example complaint letters for the AI to learn from."""
    if request.method == "POST":
        form = ExampleLetterForm(request.POST)
        if form.is_valid():
            category = form.cleaned_data["category"]
            product_name = form.cleaned_data["product"]
            letter_text = form.cleaned_data["letter_text"]

            # Use the NER and sentiment modules to auto-extract metadata
            try:
                from ml.ner import ComplaintNER
                ner = ComplaintNER()
                entities = ner.extract(letter_text)
            except ImportError:
                entities = {}

            # Use user-provided company name, fall back to NER
            company_name = form.cleaned_data.get("company_name", "").strip()
            if not company_name:
                company_name = entities.get("company_name", "")
            product = product_name or entities.get("product", "")

            # Determine company type from category/product
            company_type_map = {
                "Telecoms": "ISP / Mobile Provider",
                "Financial Services": "Bank / Financial Institution",
                "Utilities": "Energy / Water Provider",
                "Retail": "Retailer",
                "Transport": "Transport Provider",
            }
            company_type = company_type_map.get(category.name, "General")

            # Auto-detect issue type from common patterns
            text_lower = letter_text.lower()
            issue_type = "General complaint"
            issue_patterns = [
                (["outage", "down", "not working", "no service", "no signal"], "Service outage"),
                (["billing", "bill", "overcharged", "charge", "payment"], "Billing dispute"),
                (["refund", "money back", "return"], "Refund request"),
                (["delivery", "not arrived", "missing", "lost"], "Delivery issue"),
                (["faulty", "broken", "defective", "damaged"], "Faulty product"),
                (["cancel", "cancellation", "terminate"], "Cancellation issue"),
                (["delay", "late", "waiting"], "Delay"),
                (["rude", "unhelpful", "poor service", "customer service"], "Poor customer service"),
                (["contract", "agreement", "terms"], "Contract dispute"),
                (["data", "privacy", "personal information", "gdpr"], "Data/privacy issue"),
                (["upgrade", "downgrade", "switch"], "Account changes"),
                (["compensation", "redress", "reimburse"], "Compensation claim"),
            ]
            for keywords, label in issue_patterns:
                if any(kw in text_lower for kw in keywords):
                    issue_type = label
                    break

            # Auto-extract keywords from the letter
            import re
            from collections import Counter
            stopwords = {
                "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
                "for", "of", "with", "by", "from", "is", "was", "are", "were",
                "be", "been", "being", "have", "has", "had", "do", "does", "did",
                "will", "would", "could", "should", "may", "might", "can", "shall",
                "i", "me", "my", "we", "our", "you", "your", "they", "them",
                "their", "it", "its", "this", "that", "these", "those", "not",
                "no", "so", "if", "then", "than", "too", "very", "just", "am",
                "dear", "sir", "madam", "yours", "faithfully", "sincerely",
                "please", "thank", "regards", "writing", "write", "complaint",
                "formally", "formal",
            }
            words = re.findall(r"[a-z]{3,}", text_lower)
            word_counts = Counter(w for w in words if w not in stopwords)
            top_keywords = [w for w, _ in word_counts.most_common(15)]
            keywords_str = ",".join(top_keywords)

            # Convert the letter into a template by replacing specific details
            # with placeholders
            template_body = letter_text
            if company_name:
                template_body = template_body.replace(company_name, "{company}")
            if product:
                template_body = template_body.replace(product, "{product}")

            # 1. Create the ExampleLetter (for letter generation)
            example = ExampleLetter.objects.create(
                category=category,
                company_type=company_type,
                issue_type=issue_type,
                keywords=keywords_str,
                letter_body=template_body,
                source="User submitted via training page",
            )

            # 2. Create a CFPBComplaint record (for ML model training)
            timeframe = entities.get("timeframe", "")
            CFPBComplaint.objects.create(
                product=category.name,
                sub_product=product,
                issue=issue_type,
                complaint_narrative=letter_text,
                company=company_name,
                company_response="",
                submitted_via="Training page",
            )

            messages.success(
                request,
                f"Letter saved to both training datasets! "
                f"Detected: category={category.name}, "
                f"issue={issue_type}, company={company_name or 'N/A'}, "
                f"product={product or 'N/A'}, "
                f"{len(top_keywords)} keywords extracted. "
                f"Run 'python manage.py train_models' to retrain the classifier."
            )
            return redirect("complaints:train_letters")
    else:
        form = ExampleLetterForm()

    # Show existing example letters
    examples = ExampleLetter.objects.select_related("category").all()

    return render(request, "complaints/train_letters.html", {
        "form": form,
        "examples": examples,
    })


@login_required
def data_collected(request):
    """Show all categories, strategies, known companies, and product types."""
    categories = Category.objects.all()
    strategies = ComplaintStrategy.objects.select_related("category").all()

    # Top companies from CFPB data
    top_companies = (
        CFPBComplaint.objects
        .exclude(company="")
        .values("company")
        .annotate(count=Count("id"))
        .order_by("-count")[:50]
    )

    # Product types from CFPB data
    product_types = (
        CFPBComplaint.objects
        .exclude(product="")
        .values("product")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Common issues from CFPB data
    common_issues = (
        CFPBComplaint.objects
        .exclude(issue="")
        .values("issue")
        .annotate(count=Count("id"))
        .order_by("-count")[:30]
    )

    context = {
        "categories": categories,
        "strategies": strategies,
        "top_companies": top_companies,
        "product_types": product_types,
        "common_issues": common_issues,
        "cfpb_total": CFPBComplaint.objects.count(),
    }
    return render(request, "complaints/data_collected.html", context)


@login_required
def search_companies(request):
    """Search companies in the CFPB data by name."""
    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return JsonResponse({"results": []})

    results = (
        CFPBComplaint.objects
        .filter(company__icontains=query)
        .values("company")
        .annotate(count=Count("id"))
        .order_by("-count")[:20]
    )
    return JsonResponse({
        "results": [
            {"company": r["company"], "count": r["count"]}
            for r in results
        ]
    })


@login_required
def dashboard_data(request):
    """Return aggregate complaint statistics as JSON for Chart.js dashboards."""
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

    return JsonResponse(data)
