"""Utility helpers for the complaints app, including PDF letter generation."""

import io
import re
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _find_best_example_letter(complaint):
    """
    Search ExampleLetter records for the best match based on:
    1. Same category (required)
    2. Keyword overlap with the complaint text (scored)
    3. Company type / issue type similarity (scored)

    Returns the best ExampleLetter or None.
    """
    from .models import ExampleLetter

    # Search ALL example letters, not just same category
    candidates = ExampleLetter.objects.select_related("category").all()
    if not candidates.exists():
        return None

    raw_lower = complaint.raw_text.lower()
    complaint_words = set(re.findall(r"[a-z]{3,}", raw_lower))

    best_score = -1
    best_letter = None

    for letter in candidates:
        score = 0

        # Keyword matching (strongest signal)
        for kw in letter.keyword_list():
            if kw in raw_lower:
                score += 3

        # Word overlap between complaint text and letter body
        letter_words = set(re.findall(r"[a-z]{3,}", letter.letter_body.lower()))
        overlap = complaint_words & letter_words
        score += len(overlap)

        # Word overlap with issue_type
        issue_words = set(re.findall(r"[a-z]+", letter.issue_type.lower()))
        score += len(complaint_words & issue_words) * 2

        # Company type match
        if letter.company_type.lower() in raw_lower:
            score += 2
        if complaint.product and letter.company_type.lower() in complaint.product.lower():
            score += 2

        # Category match bonus
        if complaint.predicted_category and letter.category == complaint.predicted_category:
            score += 5

        if score > best_score:
            best_score = score
            best_letter = letter

    # Only return if there's meaningful overlap (score > 2 means at least
    # some keyword or word match, not just a random pick)
    return best_letter if best_score > 2 else None


def _build_complaint_summary(complaint):
    """Build a detailed summary from user input + extracted entities."""
    parts = [complaint.raw_text]
    raw_lower = complaint.raw_text.lower()

    if complaint.company_name and complaint.company_name.lower() not in raw_lower:
        parts.append(
            f"This complaint relates to services provided by {complaint.company_name}."
        )
    if complaint.product and complaint.product.lower() not in raw_lower:
        parts.append(
            f"The product/service in question is: {complaint.product}."
        )
    if complaint.timeframe and complaint.timeframe.lower() not in raw_lower:
        parts.append(
            f"This issue has been ongoing for {complaint.timeframe}."
        )

    if complaint.urgency_level == "critical":
        parts.append(
            "This matter is extremely urgent and is causing significant "
            "distress and financial impact."
        )
    elif complaint.urgency_level == "high":
        parts.append(
            "This issue is causing considerable inconvenience and requires "
            "immediate attention."
        )
    elif complaint.urgency_level == "medium":
        parts.append(
            "This matter has caused notable disruption and I expect it to "
            "be addressed promptly."
        )

    if any(w in raw_lower for w in [
        "called", "phoned", "emailed", "contacted", "told", "spoke",
    ]):
        parts.append(
            "I have already attempted to resolve this matter through your "
            "customer service channels without success."
        )

    return "\n\n".join(parts)


def _strip_greeting_closing(text, company=""):
    """Remove greetings and closings so the PDF generator can add its own."""
    # Strip any opening greeting
    text = re.sub(r"(?i)^dear\s+.*?[,.\n]", "", text.strip())
    text = re.sub(r"(?i)^to\s+whom\s+it\s+may\s+concern[,.\n]?", "", text.strip())

    # Strip standalone company name line at the start (left over from template)
    if company:
        text = re.sub(
            r"(?i)^" + re.escape(company) + r"\s*[,.]?\s*\n?",
            "", text.strip(),
        )

    # Strip any closing — catch all common sign-offs and everything after them
    closing_pattern = (
        r"(?i)\n?\s*("
        r"yours\s+(faithfully|sincerely|truly)"
        r"|kind\s+regards"
        r"|best\s+regards"
        r"|regards"
        r"|many\s+thanks"
        r"|sincerely"
        r"|with\s+thanks"
        r"|thank\s+you"
        r")[,.]?\s*\n?.*$"
    )
    text = re.sub(closing_pattern, "", text.strip(), flags=re.DOTALL)
    return text.strip()


def generate_complaint_letter_pdf(complaint) -> bytes:
    """Generate a professional complaint letter as a PDF.

    Priority for letter body:
    1. Best matching ExampleLetter (learned from data you provide)
    2. Matched strategy template (seeded defaults)
    3. Generic fallback
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]

    style_body = ParagraphStyle(
        "Body", parent=style_normal, fontSize=11, leading=16, spaceAfter=12,
    )
    style_sender = ParagraphStyle(
        "Sender", parent=style_normal, fontSize=11, leading=14,
    )
    style_subject = ParagraphStyle(
        "Subject", parent=style_normal, fontSize=12, leading=16,
        spaceAfter=12, fontName="Helvetica-Bold",
    )

    today = date.today().strftime("%d %B %Y")
    user_name = complaint.user.get_full_name() or complaint.user.username
    has_company = bool(complaint.company_name)
    company = complaint.company_name or ""
    product_name = complaint.product or "your product/service"
    timeframe = complaint.timeframe or "recently"
    summary = _build_complaint_summary(complaint)

    placeholders = {
        "company": company,
        "product": product_name,
        "complaint_summary": summary,
        "timeframe": timeframe,
        "user_name": user_name,
        "date": today,
    }

    # --- Pick the best letter body source ---
    body_text = None

    # 1. Try learned example letters first
    example = _find_best_example_letter(complaint)
    if example:
        try:
            body_text = example.letter_body.format(**placeholders)
        except KeyError:
            body_text = example.letter_body

    # 2. Fall back to strategy template
    if not body_text and complaint.matched_strategy and complaint.matched_strategy.letter_template:
        try:
            body_text = complaint.matched_strategy.letter_template.format(**placeholders)
        except KeyError:
            body_text = complaint.matched_strategy.letter_template

    # 3. Generic fallback
    if not body_text:
        body_text = (
            f"I am writing to formally complain about {product_name} "
            f"provided by {company}.\n\n"
            f"{summary}\n\n"
            f"I would appreciate a prompt resolution to this matter. Please "
            f"respond within 14 days to confirm the steps you will take to "
            f"address my complaint.\n\n"
            f"I look forward to your reply."
        )

    body_text = _strip_greeting_closing(body_text, company=company)
    body_text = body_text.replace("\n", "<br/>")

    # --- Build PDF ---
    elements = []

    elements.append(Paragraph(user_name, style_sender))
    elements.append(Paragraph(today, style_sender))
    elements.append(Spacer(1, 0.8 * cm))

    # Only show "To:" line if we have a company name
    if has_company:
        elements.append(Paragraph(f"To: {company}", style_sender))
        elements.append(Spacer(1, 0.8 * cm))

    category_label = (
        complaint.predicted_category.name if complaint.predicted_category else "General"
    )
    elements.append(Paragraph(
        f"Subject: Formal Complaint - {category_label}", style_subject,
    ))
    elements.append(Spacer(1, 0.4 * cm))

    salutation = f"Dear {company}," if has_company else "Dear Sir/Madam,"
    elements.append(Paragraph(salutation, style_body))
    elements.append(Paragraph(body_text, style_body))

    elements.append(Spacer(1, 0.6 * cm))
    elements.append(Paragraph("Yours faithfully,", style_body))
    elements.append(Spacer(1, 1.0 * cm))
    elements.append(Paragraph(user_name, style_body))

    doc.build(elements)
    return buf.getvalue()
