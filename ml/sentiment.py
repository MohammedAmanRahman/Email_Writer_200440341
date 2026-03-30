"""
Sentiment Analyzer for Complaint Texts.
Combines keyword-based scoring with urgency detection for complaint triage.
"""


class SentimentAnalyzer:
    """
    Analyses complaint text sentiment and urgency.
    Uses a keyword-based approach as baseline, producing a score from -1 to 1,
    a label (positive / neutral / negative), and an urgency rating.
    """

    # ------------------------------------------------------------------ #
    #  Word lists
    # ------------------------------------------------------------------ #
    NEGATIVE_WORDS = [
        "terrible", "awful", "horrible", "worst", "disgusting", "appalling",
        "dreadful", "unacceptable", "outrageous", "abysmal", "shocking",
        "incompetent", "useless", "pathetic", "disgraceful", "atrocious",
        "furious", "angry", "frustrated", "disappointed", "annoyed",
        "upset", "unhappy", "dissatisfied", "fed up", "livid",
        "ripped off", "scam", "fraud", "dishonest", "misleading",
        "broken", "faulty", "defective", "damaged", "rubbish",
        "nightmare", "disaster", "joke", "shambles", "ridiculous",
        "ignored", "neglected", "lied", "cheated", "overcharged",
        "poor", "bad", "wrong", "fail", "failed", "failure",
        "complaint", "complain", "problem", "issue", "error",
    ]

    POSITIVE_WORDS = [
        "good", "great", "excellent", "fantastic", "wonderful", "amazing",
        "brilliant", "outstanding", "helpful", "pleased", "satisfied",
        "happy", "thank", "thanks", "resolved", "fixed", "improved",
        "prompt", "efficient", "professional", "friendly", "courteous",
        "recommend", "impressed", "perfect", "superb", "delighted",
        "appreciate", "grateful", "reliable", "quick", "fair",
    ]

    URGENT_KEYWORDS = [
        "urgent", "immediately", "dangerous", "unsafe", "emergency",
        "legal action", "solicitor", "ombudsman", "trading standards",
        "court", "lawsuit", "sue", "lawyer", "regulator", "fca",
        "ofcom", "ofgem", "ofwat", "caa", "health and safety",
        "life threatening", "hazard", "hazardous", "risk", "death",
        "injury", "injured", "hospital", "police", "criminal",
        "deadline", "final notice", "last chance", "warning",
        "disconnection", "eviction", "bailiff", "debt collector",
    ]

    INTENSIFIERS = [
        "very", "extremely", "absolutely", "completely", "totally",
        "utterly", "incredibly", "highly", "really", "seriously",
    ]

    NEGATORS = [
        "not", "no", "never", "neither", "nor", "nobody", "nothing",
        "nowhere", "hardly", "barely", "scarcely", "don't", "doesn't",
        "didn't", "won't", "wouldn't", "shouldn't", "couldn't", "can't",
    ]

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def analyze(self, text: str) -> dict:
        """
        Analyse *text* and return a dict with:
            label  – "positive" | "neutral" | "negative"
            score  – float in [-1, 1]
            urgency – "low" | "medium" | "high" | "critical"
        """
        text_lower = text.lower()
        words = text_lower.split()

        # --- sentiment score ------------------------------------------ #
        neg_count = 0
        pos_count = 0
        intensity = 1.0

        for i, word in enumerate(words):
            clean = "".join(c for c in word if c.isalnum())
            if not clean:
                continue

            # Check for intensifiers (boost the next sentiment word)
            if clean in self.INTENSIFIERS:
                intensity = 1.5
                continue

            # Check for negators (flip the next sentiment word)
            is_negated = False
            if i > 0:
                prev = "".join(c for c in words[i - 1] if c.isalnum())
                if prev in self.NEGATORS:
                    is_negated = True

            if clean in [w.replace(" ", "") for w in self.NEGATIVE_WORDS] or \
               any(clean == nw for nw in self.NEGATIVE_WORDS if " " not in nw):
                if is_negated:
                    pos_count += 1 * intensity
                else:
                    neg_count += 1 * intensity
                intensity = 1.0
            elif clean in self.POSITIVE_WORDS:
                if is_negated:
                    neg_count += 1 * intensity
                else:
                    pos_count += 1 * intensity
                intensity = 1.0
            else:
                intensity = 1.0  # reset if unused

        # Also match multi-word negative / urgent phrases
        for phrase in self.NEGATIVE_WORDS:
            if " " in phrase and phrase in text_lower:
                neg_count += 1
        for phrase in self.POSITIVE_WORDS:
            if " " in phrase and phrase in text_lower:
                pos_count += 1

        total = neg_count + pos_count
        if total == 0:
            score = 0.0
        else:
            score = (pos_count - neg_count) / total

        # Clamp to [-1, 1]
        score = max(-1.0, min(1.0, score))

        # Label
        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"

        # --- urgency -------------------------------------------------- #
        urgent_hits = sum(
            1 for kw in self.URGENT_KEYWORDS if kw in text_lower
        )
        urgency = self._determine_urgency(score, urgent_hits)

        return {
            "label": label,
            "score": round(score, 4),
            "urgency": urgency,
        }

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _determine_urgency(sentiment_score: float, urgent_hits: int) -> str:
        """
        Derive urgency from sentiment score and the number of urgent keyword
        matches.

        Rules (highest priority first):
            critical – 3+ urgent keywords, or 2+ with very negative sentiment
            high     – any urgent keywords present, or very negative sentiment
            medium   – moderately negative sentiment
            low      – neutral or positive sentiment, no urgent keywords
        """
        if urgent_hits >= 3:
            return "critical"
        if urgent_hits >= 2 and sentiment_score < -0.4:
            return "critical"
        if urgent_hits >= 1:
            return "high"
        if sentiment_score < -0.6:
            return "high"
        if sentiment_score < -0.2:
            return "medium"
        return "low"
