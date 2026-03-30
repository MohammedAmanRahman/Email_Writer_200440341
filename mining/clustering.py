"""
Complaint Clustering - Data Mining Module
Groups complaints into clusters using TF-IDF + KMeans.
Covers: clustering, outlier detection from the Data Mining syllabus.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning(
        "scikit-learn is not installed. Clustering will not be available. "
        "Install it with: pip install scikit-learn"
    )


class ComplaintClusterer:
    """Clusters complaints using TF-IDF vectorization and KMeans."""

    def __init__(self):
        self.vectorizer = None
        self.model = None
        self.tfidf_matrix = None
        self.complaints_data = []
        self.labels = None
        self.n_clusters = 5

    def fit(self, n_clusters=5):
        """
        Vectorize complaint texts with TF-IDF and run KMeans clustering.

        Args:
            n_clusters: Number of clusters to create (default 5).

        Returns:
            True if clustering succeeded, False otherwise.
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn is required for clustering.")
            return False

        from complaints.models import Complaint

        self.n_clusters = n_clusters
        complaints = Complaint.objects.values("id", "raw_text", "sentiment_label",
                                               "sentiment_score", "urgency_level",
                                               "predicted_category__name", "company_name")

        self.complaints_data = list(complaints)

        if len(self.complaints_data) < n_clusters:
            logger.warning(
                "Not enough complaints (%d) for %d clusters.",
                len(self.complaints_data), n_clusters
            )
            return False

        texts = [c["raw_text"] for c in self.complaints_data]

        # TF-IDF vectorization
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            max_df=0.85,
            min_df=2,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)

        # KMeans clustering
        self.model = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10,
            max_iter=300,
        )
        self.labels = self.model.fit_predict(self.tfidf_matrix)

        # Store labels back into complaints_data
        for i, label in enumerate(self.labels):
            self.complaints_data[i]["cluster"] = int(label)

        return True

    def get_cluster_summaries(self):
        """
        For each cluster, get top keywords, avg sentiment, dominant category, and size.

        Returns:
            List of dicts, one per cluster, with summary info.
        """
        if self.model is None or self.labels is None:
            logger.warning("Must call fit() before get_cluster_summaries().")
            return []

        feature_names = self.vectorizer.get_feature_names_out()
        summaries = []

        for cluster_id in range(self.n_clusters):
            # Complaints in this cluster
            members = [c for c in self.complaints_data if c["cluster"] == cluster_id]
            size = len(members)

            if size == 0:
                summaries.append({
                    "cluster_id": cluster_id,
                    "size": 0,
                    "top_keywords": [],
                    "avg_sentiment": None,
                    "dominant_category": None,
                })
                continue

            # Top keywords from cluster center
            center = self.model.cluster_centers_[cluster_id]
            top_indices = center.argsort()[-10:][::-1]
            top_keywords = [feature_names[i] for i in top_indices]

            # Average sentiment score
            sentiment_scores = [
                c["sentiment_score"] for c in members
                if c["sentiment_score"] is not None
            ]
            avg_sentiment = (
                round(float(np.mean(sentiment_scores)), 4)
                if sentiment_scores else None
            )

            # Dominant category
            categories = [
                c["predicted_category__name"] for c in members
                if c["predicted_category__name"]
            ]
            dominant_category = (
                max(set(categories), key=categories.count)
                if categories else None
            )

            # Dominant urgency
            urgencies = [
                c["urgency_level"] for c in members
                if c["urgency_level"]
            ]
            dominant_urgency = (
                max(set(urgencies), key=urgencies.count)
                if urgencies else None
            )

            summaries.append({
                "cluster_id": cluster_id,
                "size": size,
                "top_keywords": top_keywords,
                "avg_sentiment": avg_sentiment,
                "dominant_category": dominant_category,
                "dominant_urgency": dominant_urgency,
            })

        return summaries

    def find_similar_complaints(self, text, n=5):
        """
        Find the most similar complaints to a given text using cosine similarity.

        Args:
            text: The query text to compare against.
            n: Number of similar complaints to return.

        Returns:
            List of dicts with complaint data and similarity score.
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn is required for similarity search.")
            return []

        if self.vectorizer is None or self.tfidf_matrix is None:
            logger.warning("Must call fit() before find_similar_complaints().")
            return []

        # Vectorize the query text
        query_vec = self.vectorizer.transform([text])

        # Compute cosine similarity against all complaints
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Get top-n indices
        top_indices = similarities.argsort()[-n:][::-1]

        results = []
        for idx in top_indices:
            complaint = self.complaints_data[idx].copy()
            complaint["similarity"] = round(float(similarities[idx]), 4)
            results.append(complaint)

        return results

    def get_outliers(self, threshold_percentile=95):
        """
        Identify complaints far from any cluster center (outlier detection).

        Outliers are complaints whose distance to their assigned cluster center
        is above the given percentile threshold.

        Args:
            threshold_percentile: Percentile above which a complaint is an outlier.

        Returns:
            List of dicts with complaint data and distance score.
        """
        if self.model is None or self.tfidf_matrix is None:
            logger.warning("Must call fit() before get_outliers().")
            return []

        # Calculate distance from each point to its assigned cluster center
        distances = []
        for i in range(len(self.complaints_data)):
            cluster_id = self.labels[i]
            center = self.model.cluster_centers_[cluster_id]
            point = self.tfidf_matrix[i].toarray().flatten()
            distance = float(np.linalg.norm(point - center))
            distances.append(distance)

        distances = np.array(distances)
        threshold = np.percentile(distances, threshold_percentile)

        outliers = []
        for i, dist in enumerate(distances):
            if dist >= threshold:
                complaint = self.complaints_data[i].copy()
                complaint["distance_to_center"] = round(dist, 4)
                outliers.append(complaint)

        # Sort by distance descending (most anomalous first)
        outliers.sort(key=lambda x: x["distance_to_center"], reverse=True)

        return outliers
