import re
from app.services.identity.interface import IdentityClaim, IdentityConsistencyModel, IdentityConsistencyResult

def _normalize_domain(domain_str):
    if not domain_str:
        return ""
    d = domain_str.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    return d.split("/")[0]

def _domain_matches(a, b):
    return _normalize_domain(a) == _normalize_domain(b)

class RuleBasedIdentityChecker(IdentityConsistencyModel):
    def evaluate(self, c: IdentityClaim) -> IdentityConsistencyResult:
        checks = []
        mismatches = []
        points = 0
        total = 0

        # Normalize domains
        email_domain = _normalize_domain(c.email_domain) if c.email_domain else ""
        website_domain = _normalize_domain(c.website_domain) if c.website_domain else ""
        official_domain = _normalize_domain(c.official_company_domain) if c.official_company_domain else ""

        # 1. Deterministic Domain Match Check
        if email_domain and website_domain:
            checks.append("email_domain_matches_website_domain")
            total += 1
            if _domain_matches(email_domain, website_domain):
                points += 1
            else:
                mismatches.append("Email domain does not match the opportunity website domain.")

        # 2. Stated Official Domain Checks
        if website_domain and official_domain:
            checks.append("website_domain_matches_official_domain")
            total += 1
            if _domain_matches(website_domain, official_domain):
                points += 1
            else:
                mismatches.append("Opportunity website domain does not match the company's official domain.")

        if email_domain and official_domain:
            checks.append("email_domain_matches_official_domain")
            total += 1
            if _domain_matches(email_domain, official_domain):
                points += 1
            else:
                mismatches.append("Recruiter email domain does not match the official company domain.")

        # 3. Probabilistic Claimed Company to Domain Similarity
        # E.g. recruiter at "Google" using domain "google-recruiting-portal.com" (contains "google" but not official)
        if c.claimed_company and (email_domain or website_domain):
            checks.append("company_name_in_domain")
            total += 1
            company_clean = c.claimed_company.strip().lower()
            
            # Check if company name is a substring of the domain
            in_email = company_clean in email_domain if email_domain else False
            in_web = company_clean in website_domain if website_domain else False
            
            if in_email or in_web:
                # Part matches (e.g. stripe-jobs.com matches stripe)
                # But check if it is the EXACT official domain
                is_exact = False
                if official_domain:
                    is_exact = _domain_matches(email_domain, official_domain) or _domain_matches(website_domain, official_domain)
                
                if is_exact:
                    points += 1
                else:
                    # Give partial points (0.5) for name inclusion, but add warning mismatch
                    points += 0.5
                    mismatches.append(f"Domain contains company name '{c.claimed_company}' but is not the official company domain.")
            else:
                mismatches.append(f"Domain name does not contain the claimed company name '{c.claimed_company}' at all.")

        # 4. Email Syntax and Format Checks
        if c.sender_email:
            checks.append("email_syntax_valid")
            total += 1
            # Basic regex match
            is_valid_email = re.match(r"^[^@]+@[^@]+\.[^@]+$", c.sender_email)
            if is_valid_email:
                points += 1
                
                # Check for free email providers (Gmail, Outlook, Yahoo) representing official company
                is_free_provider = any(free in email_domain for free in ["gmail.com", "yahoo", "outlook", "hotmail", "aol"])
                if is_free_provider and c.claimed_company:
                    checks.append("official_recruiter_using_free_email")
                    total += 1
                    # Impose penalty for official recruiter using free email
                    mismatches.append(f"Official recruiter for '{c.claimed_company}' is using a public/free email provider ({email_domain}).")
            else:
                mismatches.append("Invalid email syntax format.")

        # Calculate consistency score
        score = round(points / total, 4) if total > 0 else 0.5
        
        return IdentityConsistencyResult(
            identity_consistency_score=score,
            mismatches=mismatches,
            checks_performed=checks,
            is_demo_prediction=False
        )

def get_identity_checker():
    return RuleBasedIdentityChecker()
