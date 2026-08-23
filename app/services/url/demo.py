from app.services.url.interface import URLFeatures,URLRiskModel,URLRiskPrediction
_WEIGHTS={"has_suspicious_tld":.30,"not_https":.15,"high_entropy":.20,"high_subdomain_count":.15,"high_digit_ratio":.10,"high_special_char_ratio":.10}
class DemoURLRiskModel(URLRiskModel):
    def is_trained(self): return False
    def predict(self,f):
        c={"has_suspicious_tld":_WEIGHTS["has_suspicious_tld"] if f.has_suspicious_tld else 0.,"not_https":_WEIGHTS["not_https"] if not f.is_https else 0.,"high_entropy":_WEIGHTS["high_entropy"] if f.entropy>3.5 else 0.,"high_subdomain_count":_WEIGHTS["high_subdomain_count"] if f.subdomain_count>=3 else 0.,"high_digit_ratio":_WEIGHTS["high_digit_ratio"] if f.digit_ratio>.15 else 0.,"high_special_char_ratio":_WEIGHTS["high_special_char_ratio"] if f.special_char_ratio>.1 else 0.}
        return URLRiskPrediction(round(min(.97,sum(c.values())),4),f,c,"demo-linear-url-risk","0.1.0-demo",True)
def get_url_model():
    from app.core.config import settings
    if settings.URL_MODEL_PATH: pass
    return DemoURLRiskModel()
