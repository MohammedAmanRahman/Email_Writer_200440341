"""
Named Entity Recognition for Complaint Texts.
Extracts company names, products, timeframes, monetary values, and locations
using regex patterns with an optional spaCy enhancement layer.
"""
import re


class ComplaintNER:
    """
    Extracts structured entities from free-text complaints.

    Primary approach: hand-crafted regex patterns tuned for UK consumer
    complaints.  If spaCy is available, its NER predictions are merged in.
    """

    # ------------------------------------------------------------------ #
    #  Known entities
    # ------------------------------------------------------------------ #

    KNOWN_COMPANIES = [
        # Telecoms
        "BT", "Sky", "EE", "Vodafone", "O2", "Three", "Virgin Media",
        "TalkTalk", "Plusnet", "Hyperoptic", "Giffgaff",
        # Utilities
        "British Gas", "EDF", "EON", "E.ON", "SSE", "Scottish Power",
        "Octopus Energy", "Bulb", "OVO Energy", "Npower",
        # Finance
        "Barclays", "HSBC", "Lloyds", "NatWest", "Santander",
        "Nationwide", "Halifax", "TSB", "Monzo", "Starling",
        "Revolut", "PayPal",
        # Retail
        "Amazon", "eBay", "Argos", "John Lewis", "Currys",
        "Tesco", "Sainsburys", "Asda", "Morrisons", "Aldi", "Lidl",
        "ASOS", "Next", "Marks and Spencer", "M&S",
        # Transport
        "National Rail", "TfL", "Uber", "Ryanair", "EasyJet",
        "British Airways",
    ]

    PRODUCT_KEYWORDS = [
        "broadband", "internet", "wifi", "wi-fi", "mobile", "phone",
        "landline", "tv", "television", "fibre",
        "gas", "electricity", "electric", "water", "energy",
        "current account", "savings account", "credit card", "debit card",
        "mortgage", "loan", "insurance", "pension", "ISA",
        "washing machine", "fridge", "laptop", "computer", "tablet",
        "dishwasher", "boiler", "heating", "router",
        "train ticket", "flight", "booking",
    ]

    UK_LOCATIONS = [
        "London", "Manchester", "Birmingham", "Leeds", "Liverpool",
        "Bristol", "Sheffield", "Newcastle", "Nottingham", "Edinburgh",
        "Glasgow", "Cardiff", "Belfast", "Southampton", "Brighton",
        "Oxford", "Cambridge", "York", "Bath", "Leicester",
        "England", "Scotland", "Wales", "Northern Ireland",
        "United Kingdom", "UK",
    ]

    # ------------------------------------------------------------------ #
    #  Regex patterns
    # ------------------------------------------------------------------ #

    # Monetary: £12, £12.50, £1,234.56, GBP 100
    _RE_MONEY = re.compile(
        r"£\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?"
        r"|GBP\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?",
        re.IGNORECASE,
    )

    # Timeframes: "3 days", "two weeks", "last month", "since January",
    # "on 12/03/2024", "on 12 March 2024"
    _RE_TIMEFRAME = re.compile(
        r"\b\d+\s*(?:day|week|month|year|hour|minute)s?\b"
        r"|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
        r"\s+(?:day|week|month|year|hour|minute)s?\b"
        r"|\b(?:last|this|next|past|previous)\s+(?:day|week|month|year|monday"
        r"|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
        r"|\bsince\s+(?:january|february|march|april|may|june|july|august"
        r"|september|october|november|december|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b"
        r"|\bon\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b"
        r"|\bon\s+\d{1,2}\s+(?:january|february|march|april|may|june|july"
        r"|august|september|october|november|december)\s+\d{4}\b"
        r"|\b(?:january|february|march|april|may|june|july|august|september"
        r"|october|november|december)\s+\d{4}\b",
        re.IGNORECASE,
    )

    # Company suffix patterns (Ltd, PLC, Inc, etc.)
    _RE_COMPANY_SUFFIX = re.compile(
        r"\b([A-Z][A-Za-z&'.]+(?:\s+[A-Z][A-Za-z&'.]+)*)"
        r"\s+(?:Ltd|Limited|PLC|Inc|Corporation|Corp|Group)\b"
    )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def extract_entities(self, text: str) -> dict:
        """
        Return a dict with keys:
            company_name, product, timeframe, monetary_value, location
        Each value is a string (first / best match) or empty string.
        """
        entities = {
            "company_name": self._find_company(text),
            "product": self._find_product(text),
            "timeframe": self._find_timeframe(text),
            "monetary_value": self._find_money(text),
            "location": self._find_location(text),
        }

        # Optionally enhance with spaCy
        entities = self._spacy_enhance(text, entities)

        return entities

    def extract(self, text: str) -> dict:
        """Alias kept for API compatibility."""
        return self.extract_entities(text)

    # ------------------------------------------------------------------ #
    #  Regex matchers
    # ------------------------------------------------------------------ #

    def _find_company(self, text: str) -> str:
        # 1. Check known companies first (longest match wins)
        text_lower = text.lower()
        found = []
        for company in self.KNOWN_COMPANIES:
            if company.lower() in text_lower:
                found.append(company)
        if found:
            # Return the longest match (avoids "EE" matching inside other words
            # while still preferring "Virgin Media" over "Virgin")
            return max(found, key=len)

        # 2. Regex for "Xxx Ltd / PLC / Inc"
        m = self._RE_COMPANY_SUFFIX.search(text)
        if m:
            return m.group(0).strip()

        return ""

    def _find_product(self, text: str) -> str:
        text_lower = text.lower()
        for product in self.PRODUCT_KEYWORDS:
            if product in text_lower:
                return product
        return ""

    def _find_timeframe(self, text: str) -> str:
        m = self._RE_TIMEFRAME.search(text)
        return m.group(0).strip() if m else ""

    def _find_money(self, text: str) -> str:
        m = self._RE_MONEY.search(text)
        return m.group(0).strip() if m else ""

    def _find_location(self, text: str) -> str:
        for loc in self.UK_LOCATIONS:
            # Word-boundary match to avoid partial hits
            if re.search(r"\b" + re.escape(loc) + r"\b", text, re.IGNORECASE):
                return loc
        return ""

    # ------------------------------------------------------------------ #
    #  Optional spaCy layer
    # ------------------------------------------------------------------ #

    @staticmethod
    def _spacy_enhance(text: str, entities: dict) -> dict:
        """
        If spaCy is installed, run its NER pipeline and fill in any blanks
        left by the regex approach.
        """
        try:
            import spacy

            try:
                nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Model not downloaded -- fall back silently
                return entities

            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ == "ORG" and not entities["company_name"]:
                    entities["company_name"] = ent.text
                elif ent.label_ == "MONEY" and not entities["monetary_value"]:
                    entities["monetary_value"] = ent.text
                elif ent.label_ == "DATE" and not entities["timeframe"]:
                    entities["timeframe"] = ent.text
                elif ent.label_ == "GPE" and not entities["location"]:
                    entities["location"] = ent.text

        except ImportError:
            pass  # spaCy not installed -- regex results are good enough

        return entities
