import re
from app.services.entities.interface import EntityExtractor, ExtractedEntity, ExtractionResult

class RealEntityExtractor(EntityExtractor):
    def extract(self, text: str) -> ExtractionResult:
        text = text or ""
        entities = []

        # 1. Extract Email Addresses
        emails = re.findall(r"\b[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b", text)
        full_emails = re.findall(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", text)
        for email in full_emails:
            entities.append(ExtractedEntity(
                entity_type="email",
                value=email.lower(),
                confidence=0.99,
                source="regex_email"
            ))
            # Also extract the domain
            domain = email.split("@")[-1].lower()
            entities.append(ExtractedEntity(
                entity_type="email_domain",
                value=domain,
                confidence=0.95,
                source="regex_email_domain"
            ))

        # 2. Extract Website URLs / Domains
        urls = re.findall(r"\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)\b", text)
        for url in urls:
            # Filter out common TLDs or text that isn't a domain, but keep valid ones
            if "." in url and not url.endswith((".", "jpg", "png", "pdf", "exe", "zip")):
                # Don't add email domains if we already extracted them or keep them distinct
                entities.append(ExtractedEntity(
                    entity_type="website_domain",
                    value=url.lower(),
                    confidence=0.90,
                    source="regex_domain"
                ))

        # 3. Extract Claimed Company
        # Look for company names after typical recruiting intro structures
        company_patterns = [
            r"\b(?:work|job|career|position)\s+at\s+([A-Z][a-zA-Z0-9\s]+?)(?:\.|\s+is|\s+offers|\s+for|\s+starts|\n|\b)",
            r"\brecruiter\s+from\s+([A-Z][a-zA-Z0-9\s]+?)(?:\.|\s+is|\s+offers|\s+for|\s+starts|\n|\b)",
            r"\brepresenting\s+([A-Z][a-zA-Z0-9\s]+?)(?:\.|\s+is|\s+offers|\s+for|\s+starts|\n|\b)",
            r"\bwelcome\s+to\s+([A-Z][a-zA-Z0-9\s]+?)(?:\.|\s+is|\s+offers|\s+for|\s+starts|\n|\b)",
        ]
        
        found_companies = []
        for pat in company_patterns:
            matches = re.findall(pat, text)
            for m in matches:
                name = m.strip()
                # Stop if it captures too many words
                words = name.split()
                if len(words) <= 3 and name not in found_companies:
                    found_companies.append(name)
                    entities.append(ExtractedEntity(
                        entity_type="claimed_company",
                        value=name,
                        confidence=0.85,
                        source="pattern_company"
                    ))

        # Common fallback company detection (known companies in text)
        known_companies = ["Google", "Stripe", "Amazon", "Netflix", "Microsoft", "Meta", "Apple", "Paypal", "TCS", "Infosys"]
        for comp in known_companies:
            if re.search(r"\b" + re.escape(comp) + r"\b", text, re.IGNORECASE) and comp not in found_companies:
                entities.append(ExtractedEntity(
                    entity_type="claimed_company",
                    value=comp,
                    confidence=0.80,
                    source="known_company_dictionary"
                ))

        # 4. Extract Payments / Salaries
        payment_patterns = [
            r"\$\d+(?:,\d{3})*(?:\.\d{2})?",
            r"Rs\.\s*\d+",
            r"\b\d+\s*(?:dollars|usd|rupees|inr)\b"
        ]
        for pat in payment_patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                entities.append(ExtractedEntity(
                    entity_type="payment_amount",
                    value=m,
                    confidence=0.95,
                    source="regex_payment"
                ))

        # 5. Extract Recruiter Name
        recruiter_patterns = [
            r"\bmy\s+name\s+is\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
            r"\bthis\s+is\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b\s+from",
            r"\bregards,?\s*\n+([A-Z][a-z]+\s+[A-Z][a-z]+)\b"
        ]
        for pat in recruiter_patterns:
            matches = re.findall(pat, text)
            for m in matches:
                entities.append(ExtractedEntity(
                    entity_type="recruiter_name",
                    value=m,
                    confidence=0.80,
                    source="pattern_recruiter"
                ))

        return ExtractionResult(entities=entities)

def get_entity_extractor():
    return RealEntityExtractor()
