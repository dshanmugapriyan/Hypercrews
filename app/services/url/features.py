import math,re
from urllib.parse import urlparse
from app.services.url.interface import URLFeatures
_SUSPICIOUS_TLDS={"zip","xyz","top","gq","tk","ml","cf","work","click","loan"}
def _shannon_entropy(s):
    if not s:return 0.
    probs=[s.count(c)/len(s) for c in set(s)]
    return round(-sum(p*math.log2(p) for p in probs),4)
def extract_url_features(raw_url):
    parsed=urlparse(raw_url if "://" in raw_url else f"http://{raw_url}")
    hostname=parsed.hostname or ""; labels=hostname.split(".") if hostname else []; tld=labels[-1].lower() if len(labels)>1 else ""
    digits=sum(c.isdigit() for c in raw_url); specials=len(re.findall(r"[^a-zA-Z0-9./:_-]",raw_url))
    return URLFeatures(raw_url,len(raw_url),len(hostname),max(0,len(labels)-2),round(digits/len(raw_url),4) if raw_url else 0.,round(specials/len(raw_url),4) if raw_url else 0.,_shannon_entropy(hostname),tld in _SUSPICIOUS_TLDS,parsed.scheme=="https",0,None,None)
