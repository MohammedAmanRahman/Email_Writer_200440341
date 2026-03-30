"""
Association Rule Mining - Data Mining Module
Discovers associations between complaint attributes using the Apriori algorithm.
Covers: association analysis from the Data Mining syllabus.
"""
import logging

logger = logging.getLogger(__name__)

try:
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder
    import pandas as pd
    MLXTEND_AVAILABLE = True
except ImportError:
    MLXTEND_AVAILABLE = False
    logger.warning(
        "mlxtend is not installed. Association rule mining will not be available. "
        "Install it with: pip install mlxtend"
    )


class AssociationMiner:
    """Discovers association rules in complaint data using the Apriori algorithm."""

    def __init__(self):
        self.transactions = []
        self.frequent_itemsets = None
        self.rules = None

    def prepare_transactions(self):
        """
        Convert complaints into transactions (sets of features).
        Each transaction is a set of items like:
            {'category:Billing', 'sentiment:negative', 'urgency:high', 'company:Acme', 'product:Credit Card'}
        """
        from complaints.models import Complaint

        complaints = Complaint.objects.select_related("predicted_category").all()
        self.transactions = []

        for c in complaints:
            items = set()

            # Category
            if c.predicted_category:
                items.add(f"category:{c.predicted_category.name}")

            # Sentiment
            if c.sentiment_label:
                items.add(f"sentiment:{c.sentiment_label}")

            # Urgency
            if c.urgency_level:
                items.add(f"urgency:{c.urgency_level}")

            # Company (only include if present)
            if c.company_name:
                items.add(f"company:{c.company_name}")

            # Product (only include if present)
            if c.product:
                items.add(f"product:{c.product}")

            if len(items) >= 2:
                self.transactions.append(list(items))

        return self.transactions

    def find_rules(self, min_support=0.05, min_confidence=0.5):
        """
        Run Apriori algorithm and generate association rules.

        Args:
            min_support: Minimum support threshold (default 0.05 = 5%).
            min_confidence: Minimum confidence threshold (default 0.5 = 50%).

        Returns:
            DataFrame of association rules, or None if mlxtend is not installed.
        """
        if not MLXTEND_AVAILABLE:
            logger.error("mlxtend is required for association rule mining.")
            return None

        if not self.transactions:
            self.prepare_transactions()

        if len(self.transactions) < 5:
            logger.warning("Not enough transactions for meaningful association rules.")
            return None

        # Encode transactions into a one-hot DataFrame
        te = TransactionEncoder()
        te_array = te.fit(self.transactions).transform(self.transactions)
        df = pd.DataFrame(te_array, columns=te.columns_)

        # Find frequent itemsets using Apriori
        self.frequent_itemsets = apriori(
            df, min_support=min_support, use_colnames=True
        )

        if self.frequent_itemsets.empty:
            logger.info("No frequent itemsets found at min_support=%.3f", min_support)
            return None

        # Generate association rules
        self.rules = association_rules(
            self.frequent_itemsets, metric="confidence", min_threshold=min_confidence
        )

        # Sort by lift (how much more likely the consequent is given the antecedent)
        if not self.rules.empty:
            self.rules = self.rules.sort_values("lift", ascending=False)

        return self.rules

    def get_strategy_associations(self):
        """
        Find which complaint strategies work best for specific
        category + sentiment combinations.

        Returns a list of dicts with antecedent, consequent, confidence, lift.
        """
        if self.rules is None:
            self.find_rules(min_support=0.03, min_confidence=0.4)

        if self.rules is None or self.rules.empty:
            return []

        results = []
        for _, row in self.rules.iterrows():
            antecedents = set(row["antecedents"])
            consequents = set(row["consequents"])

            # Look for rules where antecedent involves category/sentiment
            # and consequent involves urgency or other actionable attributes
            has_category = any(item.startswith("category:") for item in antecedents)
            has_sentiment = any(item.startswith("sentiment:") for item in antecedents)

            if has_category or has_sentiment:
                results.append({
                    "antecedent": ", ".join(sorted(antecedents)),
                    "consequent": ", ".join(sorted(consequents)),
                    "confidence": round(float(row["confidence"]), 4),
                    "lift": round(float(row["lift"]), 4),
                    "support": round(float(row["support"]), 4),
                })

        return results

    def format_rules(self):
        """
        Return human-readable list of association rules.

        Returns:
            List of dicts with readable rule strings and metrics.
        """
        if self.rules is None:
            self.find_rules()

        if self.rules is None or self.rules.empty:
            return []

        formatted = []
        for _, row in self.rules.iterrows():
            ant = ", ".join(sorted(row["antecedents"]))
            con = ", ".join(sorted(row["consequents"]))
            formatted.append({
                "rule": f"{ant}  =>  {con}",
                "support": round(float(row["support"]), 4),
                "confidence": round(float(row["confidence"]), 4),
                "lift": round(float(row["lift"]), 4),
            })

        return formatted
