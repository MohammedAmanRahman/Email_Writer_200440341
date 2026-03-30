"""
Django management command to download and load CFPB complaint data.

Usage:
    python manage.py load_data
    python manage.py load_data --limit 50000
    python manage.py load_data --file data/complaints.csv
"""
import sys
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Download and load CFPB complaint data into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100000,
            help="Maximum number of rows to load (default: 100000)",
        )
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to local CSV file (skips download)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing CFPB data before loading",
        )

    def handle(self, *args, **options):
        from complaints.models import CFPBComplaint, Category

        limit = options["limit"]
        csv_file = options["file"]
        clear = options["clear"]

        if clear:
            count = CFPBComplaint.objects.count()
            CFPBComplaint.objects.all().delete()
            self.stdout.write(f"Cleared {count} existing CFPB records.")

        # Get CSV path
        if csv_file:
            csv_path = Path(csv_file)
            if not csv_path.exists():
                self.stderr.write(f"File not found: {csv_path}")
                sys.exit(1)
        else:
            from data.load_cfpb import download_cfpb_data
            csv_path = download_cfpb_data()

        # Parse and load
        from data.load_cfpb import parse_cfpb_csv

        self.stdout.write(f"Loading up to {limit} records from {csv_path}...")

        batch = []
        batch_size = 5000
        total = 0
        narratives_count = 0

        for row in parse_cfpb_csv(csv_path, limit=limit):
            # Parse date
            date_received = None
            date_str = row.get("Date received", "")
            if date_str:
                try:
                    date_received = datetime.strptime(date_str, "%m/%d/%Y").date()
                except ValueError:
                    try:
                        date_received = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass

            narrative = row.get("Consumer complaint narrative", "")
            if narrative and narrative.strip():
                narratives_count += 1

            timely = row.get("Timely response?", "").lower() == "yes"
            disputed = row.get("Consumer disputed?", "")
            consumer_disputed = None
            if disputed.lower() == "yes":
                consumer_disputed = True
            elif disputed.lower() == "no":
                consumer_disputed = False

            record = CFPBComplaint(
                date_received=date_received,
                product=row.get("Product", "")[:200],
                sub_product=row.get("Sub-product", "")[:200],
                issue=row.get("Issue", "")[:300],
                sub_issue=row.get("Sub-issue", "")[:300],
                complaint_narrative=narrative,
                company=row.get("Company", "")[:200],
                state=row.get("State", "")[:10],
                submitted_via=row.get("Submitted via", "")[:50],
                company_response=row.get("Company response to consumer", "")[:200],
                timely_response=timely,
                consumer_disputed=consumer_disputed,
            )
            batch.append(record)
            total += 1

            if len(batch) >= batch_size:
                CFPBComplaint.objects.bulk_create(batch)
                self.stdout.write(f"  Loaded {total} records...")
                batch = []

        # Final batch
        if batch:
            CFPBComplaint.objects.bulk_create(batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! Loaded {total} CFPB complaints "
                f"({narratives_count} with narrative text)."
            )
        )

        # Create default categories from product types
        products = (
            CFPBComplaint.objects.values_list("product", flat=True)
            .distinct()
        )
        created = 0
        for product in products:
            if product:
                _, is_new = Category.objects.get_or_create(
                    name=product,
                    defaults={"description": f"CFPB category: {product}"},
                )
                if is_new:
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Created {created} categories from CFPB products.")
        )
