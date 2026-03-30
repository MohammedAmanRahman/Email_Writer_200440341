"""
Management command to run data mining analysis.
Usage:
    python manage.py run_analysis              # Run all analyses
    python manage.py run_analysis --type patterns
    python manage.py run_analysis --type associations
    python manage.py run_analysis --type clustering
"""
import json
import time
from datetime import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run data mining analysis: patterns, association rules, and clustering."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            type=str,
            default="all",
            choices=["patterns", "associations", "clustering", "all"],
            help="Type of analysis to run (default: all).",
        )
        parser.add_argument(
            "--clusters",
            type=int,
            default=5,
            help="Number of clusters for KMeans (default: 5).",
        )
        parser.add_argument(
            "--min-support",
            type=float,
            default=0.05,
            help="Minimum support for Apriori (default: 0.05).",
        )
        parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.5,
            help="Minimum confidence for association rules (default: 0.5).",
        )

    def handle(self, *args, **options):
        analysis_type = options["type"]
        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}"
            f"\n  Data Mining Analysis"
            f"\n  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            f"\n  Type: {analysis_type}"
            f"\n{'='*60}\n"
        ))

        if analysis_type in ("patterns", "all"):
            self._run_patterns()

        if analysis_type in ("associations", "all"):
            self._run_associations(
                min_support=options["min_support"],
                min_confidence=options["min_confidence"],
            )

        if analysis_type in ("clustering", "all"):
            self._run_clustering(n_clusters=options["clusters"])

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}"
            f"\n  Analysis complete."
            f"\n{'='*60}\n"
        ))

    def _run_patterns(self):
        """Run pattern analysis and print results."""
        from mining.analysis import ComplaintAnalyzer

        self.stdout.write(self.style.HTTP_INFO("\n--- Pattern Analysis ---\n"))
        start = time.time()
        analyzer = ComplaintAnalyzer()

        # Category distribution
        categories = analyzer.get_category_distribution()
        self.stdout.write(f"Category distribution ({len(categories)} categories):")
        for cat in categories[:10]:
            self.stdout.write(
                f"  {cat['predicted_category__name']}: {cat['count']}"
            )

        # Sentiment distribution
        sentiments = analyzer.get_sentiment_distribution()
        self.stdout.write(f"\nSentiment distribution ({len(sentiments)} labels):")
        for s in sentiments:
            self.stdout.write(f"  {s['sentiment_label']}: {s['count']}")

        # Urgency distribution
        urgencies = analyzer.get_urgency_distribution()
        self.stdout.write(f"\nUrgency distribution ({len(urgencies)} levels):")
        for u in urgencies:
            self.stdout.write(f"  {u['urgency_level']}: {u['count']}")

        # Company stats
        companies = analyzer.get_company_stats()
        self.stdout.write(f"\nTop companies ({len(companies)} shown):")
        for c in companies[:5]:
            avg = c['avg_sentiment']
            avg_str = f"{avg:.3f}" if avg is not None else "N/A"
            self.stdout.write(
                f"  {c['company_name']}: {c['count']} complaints, "
                f"avg sentiment: {avg_str}"
            )

        # Resolution rates
        rates = analyzer.get_resolution_rates()
        if rates:
            self.stdout.write(f"\nResolution rates (CFPB data):")
            self.stdout.write(f"  Total CFPB complaints: {rates['total']}")
            self.stdout.write(
                f"  Timely response rate: {rates['timely_response_rate']:.2%}"
            )
            self.stdout.write(f"  Dispute rate: {rates['dispute_rate']:.2%}")
        else:
            self.stdout.write("\nNo CFPB data available for resolution rates.")

        # Top keywords
        keywords = analyzer.get_keyword_analysis(top_n=15)
        self.stdout.write(f"\nTop keywords ({len(keywords)} shown):")
        for word, count in keywords:
            self.stdout.write(f"  {word}: {count}")

        elapsed = time.time() - start
        self.stdout.write(
            self.style.SUCCESS(f"\nPattern analysis completed in {elapsed:.2f}s")
        )

    def _run_associations(self, min_support, min_confidence):
        """Run association rule mining and print results."""
        from mining.association import AssociationMiner, MLXTEND_AVAILABLE

        self.stdout.write(self.style.HTTP_INFO("\n--- Association Rule Mining ---\n"))

        if not MLXTEND_AVAILABLE:
            self.stdout.write(self.style.WARNING(
                "mlxtend is not installed. Skipping association rules.\n"
                "Install with: pip install mlxtend"
            ))
            return

        start = time.time()
        miner = AssociationMiner()

        transactions = miner.prepare_transactions()
        self.stdout.write(f"Prepared {len(transactions)} transactions.")

        rules = miner.find_rules(
            min_support=min_support,
            min_confidence=min_confidence,
        )

        if rules is None or (hasattr(rules, 'empty') and rules.empty):
            self.stdout.write(self.style.WARNING("No association rules found."))
        else:
            formatted = miner.format_rules()
            self.stdout.write(f"Found {len(formatted)} association rules:\n")
            for r in formatted[:15]:
                self.stdout.write(
                    f"  {r['rule']}\n"
                    f"    support={r['support']}, confidence={r['confidence']}, "
                    f"lift={r['lift']}\n"
                )

            # Strategy associations
            strategies = miner.get_strategy_associations()
            if strategies:
                self.stdout.write(f"\nStrategy associations ({len(strategies)}):")
                for s in strategies[:10]:
                    self.stdout.write(
                        f"  {s['antecedent']}  =>  {s['consequent']}\n"
                        f"    confidence={s['confidence']}, lift={s['lift']}\n"
                    )

        elapsed = time.time() - start
        self.stdout.write(
            self.style.SUCCESS(f"\nAssociation analysis completed in {elapsed:.2f}s")
        )

    def _run_clustering(self, n_clusters):
        """Run clustering analysis and print results."""
        from mining.clustering import ComplaintClusterer, SKLEARN_AVAILABLE

        self.stdout.write(self.style.HTTP_INFO("\n--- Clustering Analysis ---\n"))

        if not SKLEARN_AVAILABLE:
            self.stdout.write(self.style.WARNING(
                "scikit-learn is not installed. Skipping clustering.\n"
                "Install with: pip install scikit-learn"
            ))
            return

        start = time.time()
        clusterer = ComplaintClusterer()

        success = clusterer.fit(n_clusters=n_clusters)
        if not success:
            self.stdout.write(self.style.WARNING(
                "Clustering failed. Not enough data."
            ))
            return

        summaries = clusterer.get_cluster_summaries()
        self.stdout.write(f"Created {len(summaries)} clusters:\n")

        for s in summaries:
            self.stdout.write(
                f"  Cluster {s['cluster_id']} ({s['size']} complaints):"
            )
            self.stdout.write(
                f"    Top keywords: {', '.join(s['top_keywords'][:5])}"
            )
            avg = s['avg_sentiment']
            avg_str = f"{avg:.3f}" if avg is not None else "N/A"
            self.stdout.write(f"    Avg sentiment: {avg_str}")
            self.stdout.write(f"    Dominant category: {s['dominant_category']}")
            self.stdout.write(f"    Dominant urgency: {s['dominant_urgency']}")
            self.stdout.write("")

        # Outliers
        outliers = clusterer.get_outliers()
        self.stdout.write(f"Detected {len(outliers)} outliers (95th percentile):")
        for o in outliers[:5]:
            text_preview = o["raw_text"][:80] + "..." if len(o["raw_text"]) > 80 else o["raw_text"]
            self.stdout.write(
                f"  Distance: {o['distance_to_center']:.4f} | {text_preview}"
            )

        elapsed = time.time() - start
        self.stdout.write(
            self.style.SUCCESS(f"\nClustering analysis completed in {elapsed:.2f}s")
        )
