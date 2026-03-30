"""
Seed the database with default categories and complaint strategies.

Usage:
    python manage.py seed_data
"""
from django.core.management.base import BaseCommand


CATEGORIES = [
    ("Financial Services", "Banking, credit cards, loans, mortgages, insurance, investments"),
    ("Telecoms", "Broadband, mobile, phone contracts, internet services"),
    ("Utilities", "Gas, electricity, water, energy providers"),
    ("Retail", "Online shopping, deliveries, refunds, product faults, warranties"),
    ("Transport", "Trains, buses, flights, taxis, delays, cancellations"),
    ("Property", "Rental property, landlords, plumbing, heating, building work, repairs"),
]

STRATEGIES = [
    {
        "category": "Financial Services",
        "title": "Formal FCA-Referenced Complaint",
        "strategy_text": "Reference FCA regulations and the Financial Ombudsman Service. Cite specific account details and timeline. Request written response within 8 weeks as per FCA guidelines.",
        "success_rate": 0.72,
        "letter_template": """Dear Sir/Madam,

I am writing to formally complain about the service I have received from {company} regarding {product}.

{complaint_summary}

This issue has been ongoing for {timeframe}. I believe this falls below the standards expected under FCA regulations and your own terms of service.

I request that you:
1. Investigate this matter thoroughly
2. Provide a full written response within 8 weeks as required by FCA guidelines
3. Offer appropriate redress for the inconvenience caused

If I do not receive a satisfactory response, I will escalate this complaint to the Financial Ombudsman Service.

Yours faithfully,
{user_name}
{date}""",
    },
    {
        "category": "Telecoms",
        "title": "Ofcom-Referenced Service Complaint",
        "strategy_text": "Reference Ofcom regulations and the relevant ombudsman (CISAS or Ombudsman Services). Document service outages with dates. Request compensation for service disruption.",
        "success_rate": 0.68,
        "letter_template": """Dear Sir/Madam,

I am writing to formally complain about {product} services provided by {company}.

{complaint_summary}

This situation has persisted for {timeframe}, during which I have been unable to use the service I am paying for.

Under Ofcom's guidelines, I am entitled to adequate service and appropriate compensation for prolonged outages. I request:
1. An immediate resolution to this issue
2. Compensation for the period of disrupted service
3. A written response within 14 days

Should this not be resolved satisfactorily, I will escalate to the relevant Alternative Dispute Resolution scheme.

Yours faithfully,
{user_name}
{date}""",
    },
    {
        "category": "Utilities",
        "title": "Energy Ombudsman Escalation",
        "strategy_text": "Reference Ofgem regulations for energy or Ofwat for water. Document billing discrepancies with meter readings. Threaten ombudsman escalation after 8 weeks.",
        "success_rate": 0.65,
        "letter_template": """Dear Sir/Madam,

I wish to raise a formal complaint regarding my {product} account with {company}.

{complaint_summary}

This matter has remained unresolved for {timeframe}. As a regulated utility provider, you are required to handle complaints fairly and promptly.

I require:
1. A thorough review of my account and the issues raised
2. Correction of any billing errors
3. Confirmation of resolution in writing within 8 weeks

If this complaint is not resolved to my satisfaction, I will refer it to the Energy Ombudsman.

Yours faithfully,
{user_name}
{date}""",
    },
    {
        "category": "Retail",
        "title": "Consumer Rights Act Complaint",
        "strategy_text": "Reference the Consumer Rights Act 2015. Assert right to refund within 30 days, or repair/replacement within 6 months. Include order numbers and delivery evidence.",
        "success_rate": 0.75,
        "letter_template": """Dear Sir/Madam,

I am writing to complain about a {product} purchased from {company}.

{complaint_summary}

Under the Consumer Rights Act 2015, goods must be of satisfactory quality, fit for purpose, and as described. The product/service I received does not meet these standards.

It has now been {timeframe} since I first raised this issue. I am entitled to:
1. A full refund (if within 30 days of purchase)
2. A repair or replacement (if within 6 months)
3. Compensation for any additional losses incurred

Please respond within 14 days. If I do not receive a satisfactory resolution, I will pursue this through the Small Claims Court.

Yours faithfully,
{user_name}
{date}""",
    },
    {
        "category": "Transport",
        "title": "Delay Repay & Regulatory Complaint",
        "strategy_text": "Reference specific delay repay schemes (e.g., Delay Repay 15/30). Include journey details, ticket cost, and delay duration. Cite National Rail Conditions of Travel.",
        "success_rate": 0.70,
        "letter_template": """Dear Sir/Madam,

I wish to make a formal complaint regarding a journey with {company} involving {product}.

{complaint_summary}

This disruption occurred {timeframe}. Under the National Rail Conditions of Travel and your Delay Repay scheme, I am entitled to compensation.

I request:
1. Full compensation under the applicable Delay Repay scheme
2. An explanation for the disruption
3. Details of what measures are being taken to prevent recurrence

If this complaint is not resolved within 20 working days, I will escalate to Transport Focus.

Yours faithfully,
{user_name}
{date}""",
    },
]


class Command(BaseCommand):
    help = "Seed the database with default categories and complaint strategies"

    def handle(self, *args, **options):
        from complaints.models import Category, ComplaintStrategy

        # Create categories
        for name, description in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                name=name,
                defaults={"description": description},
            )
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {cat.name}")

        # Create strategies
        for s in STRATEGIES:
            cat = Category.objects.get(name=s["category"])
            strategy, created = ComplaintStrategy.objects.get_or_create(
                category=cat,
                title=s["title"],
                defaults={
                    "strategy_text": s["strategy_text"],
                    "success_rate": s["success_rate"],
                    "letter_template": s["letter_template"],
                },
            )
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {strategy.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeded {len(CATEGORIES)} categories and {len(STRATEGIES)} strategies."
            )
        )
