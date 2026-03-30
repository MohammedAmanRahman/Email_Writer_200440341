"""
Unified prediction interface for the complaint analysis pipeline.
Orchestrates classification, sentiment analysis, and NER.
"""
import os
import torch
from pathlib import Path
from django.conf import settings


class ComplaintPredictor:
    """Orchestrates all ML components for complaint analysis."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.model_dir = Path(settings.ML_MODEL_DIR)
        self.classifier = None
        self.preprocessor = None
        self.categories = []
        self.sentiment_analyzer = None
        self.ner = None
        self._load_components()

    def _load_components(self):
        from .sentiment import SentimentAnalyzer
        from .ner import ComplaintNER

        self.sentiment_analyzer = SentimentAnalyzer()
        self.ner = ComplaintNER()

        # Try to load trained classifier
        model_path = self.model_dir / "lstm_classifier.pt"
        vocab_path = self.model_dir / "vocab.json"
        categories_path = self.model_dir / "categories.json"

        if model_path.exists() and vocab_path.exists() and categories_path.exists():
            import json
            from .classifier import LSTMClassifier, TextPreprocessor

            with open(categories_path) as f:
                self.categories = json.load(f)

            self.preprocessor = TextPreprocessor()
            self.preprocessor.load(str(vocab_path))

            self.classifier = LSTMClassifier(
                vocab_size=self.preprocessor.vocab_size,
                embedding_dim=128,
                hidden_dim=256,
                output_dim=len(self.categories),
            )
            self.classifier.load_state_dict(
                torch.load(str(model_path), map_location="cpu", weights_only=True)
            )
            self.classifier.eval()

    def analyze_complaint(self, complaint):
        """
        Run full analysis pipeline on a complaint.
        Returns dict with category, sentiment, urgency, entities, strategy.
        """
        text = complaint.raw_text
        results = {}

        # 1. Classification
        if self.classifier and self.preprocessor:
            encoded = self.preprocessor.encode_batch([text])
            with torch.no_grad():
                output = self.classifier(encoded)
                probs = torch.softmax(output, dim=1)
                confidence, predicted = probs.max(dim=1)
            results["category"] = self.categories[predicted.item()]
            results["confidence"] = round(confidence.item(), 4)
        else:
            results["category"] = self._rule_based_classify(text)
            results["confidence"] = 0.5

        # 2. Sentiment & Urgency
        sentiment = self.sentiment_analyzer.analyze(text)
        results["sentiment_label"] = sentiment["label"]
        results["sentiment_score"] = sentiment["score"]
        results["urgency"] = sentiment["urgency"]

        # 3. NER
        entities = self.ner.extract(text)
        results["entities"] = entities
        results["company_name"] = entities.get("company_name", "")
        results["product"] = entities.get("product", "")
        results["timeframe"] = entities.get("timeframe", "")

        # 4. Apply results to complaint object
        self._apply_results(complaint, results)

        # 5. Match strategy
        self._match_strategy(complaint)

        return results

    def _rule_based_classify(self, text):
        """Fallback keyword-based classification when no model is trained."""
        text_lower = text.lower()
        keyword_map = {
            "Financial Services": [
                "bank", "credit", "loan", "mortgage", "interest rate",
                "overdraft", "savings", "investment", "insurance", "pension",
            ],
            "Telecoms": [
                "broadband", "phone", "mobile", "internet", "wifi", "signal",
                "data", "contract", "sim", "roaming", "bt", "sky", "ee",
                "vodafone", "o2", "three",
            ],
            "Utilities": [
                "gas", "electric", "water", "energy", "bill", "meter",
                "tariff", "british gas", "edf", "eon", "sse",
            ],
            "Retail": [
                "delivery", "refund", "return", "product", "order",
                "warranty", "faulty", "damaged", "shop", "store",
                "amazon", "ebay",
            ],
            "Transport": [
                "train", "bus", "flight", "delay", "cancellation", "ticket",
                "fare", "rail", "airline", "tfl",
            ],
            "Property": [
                "landlord", "tenant", "lease", "rent", "property", "repair",
                "plumbing", "pipe", "leak", "heating", "boiler", "damp",
                "mould", "roof", "building", "flat", "house", "letting",
                "estate agent",
            ],
        }

        # Also pull keywords from user-added ExampleLetters so the
        # classifier learns new categories automatically
        try:
            from complaints.models import ExampleLetter
            for letter in ExampleLetter.objects.select_related("category").all():
                cat_name = letter.category.name
                if cat_name not in keyword_map:
                    keyword_map[cat_name] = []
                keyword_map[cat_name].extend(letter.keyword_list())
        except Exception:
            pass

        scores = {}
        for cat, keywords in keyword_map.items():
            scores[cat] = sum(1 for kw in keywords if kw in text_lower)
        if not scores or max(scores.values()) == 0:
            return "Financial Services"
        return max(scores, key=scores.get)

    def _apply_results(self, complaint, results):
        """Update complaint model with analysis results."""
        from complaints.models import Category

        cat, _ = Category.objects.get_or_create(name=results["category"])
        complaint.predicted_category = cat
        complaint.category_confidence = results["confidence"]
        complaint.sentiment_label = results["sentiment_label"]
        complaint.sentiment_score = results["sentiment_score"]
        complaint.urgency_level = results["urgency"]
        complaint.entities = results["entities"]
        # Only fill in NER results if the user didn't already provide them
        if not complaint.company_name:
            complaint.company_name = results.get("company_name", "")
        if not complaint.product:
            complaint.product = results.get("product", "")
        if not complaint.timeframe:
            complaint.timeframe = results.get("timeframe", "")
        complaint.save()

    def _match_strategy(self, complaint):
        """Find best matching complaint strategy."""
        from complaints.models import ComplaintStrategy

        if complaint.predicted_category:
            strategy = (
                ComplaintStrategy.objects
                .filter(category=complaint.predicted_category)
                .order_by("-success_rate")
                .first()
            )
            if strategy:
                complaint.matched_strategy = strategy
                complaint.save()


def analyze_complaint(complaint):
    """Convenience function for views to call."""
    predictor = ComplaintPredictor.get_instance()
    return predictor.analyze_complaint(complaint)
