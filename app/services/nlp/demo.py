from app.services.nlp.interface import NLPModel, NLPPrediction
_PAYMENT_TERMS=("registration fee","processing fee","security deposit","pay now","advance payment","gpay","upi","wire transfer")
_URGENCY_TERMS=("act now","limited slots","immediately","within 24 hours","hurry","urgent","today only")
_CREDENTIAL_TERMS=("send your password","otp","bank details","aadhaar","card number","cvv")
_IDENTITY_TERMS=("no interview","no experience needed","guaranteed placement","instant offer")
_CATEGORIES=("payment_scam","company_impersonation","phishing","unrealistic_compensation","legitimate")
def _keyword_hits(text,terms): return [t for t in terms if t in (text or "").lower()]
class DemoNLPModel(NLPModel):
    def is_fine_tuned(self): return False
    def predict(self,text):
        text=text or ""; p=_keyword_hits(text,_PAYMENT_TERMS); u=_keyword_hits(text,_URGENCY_TERMS); c=_keyword_hits(text,_CREDENTIAL_TERMS); i=_keyword_hits(text,_IDENTITY_TERMS)
        payment=min(1.0,.2*len(p)); social=min(1.0,.2*len(u)+.15*len(c)); identity=min(1.0,.25*len(i)); opportunity=min(1.0,.15*len(i)+.1*len(u))
        signals=p+u+c+i; scam=min(.97,.12+.11*len(signals)) if signals else .08
        scores={"payment_scam":payment,"company_impersonation":identity*.6,"phishing":min(1.,.3*len(c)),"unrealistic_compensation":identity*.4,"legitimate":max(0.,1.-scam)}
        total=sum(scores.values()) or 1.; normalized={k:round(v/total,4) for k,v in scores.items()}
        attrs=[(t,.85) for t in p]+[(t,.7) for t in u]+[(t,.9) for t in c]+[(t,.65) for t in i]
        return NLPPrediction(round(scam,4),normalized,round(max(payment,social,identity),4),round(payment,4),round(identity,4),round(social,4),round(opportunity,4),attrs,"demo-keyword-nlp","0.1.0-demo",True)
def get_nlp_model():
    from app.core.config import settings
    if settings.NLP_MODEL_PATH:
        pass
    return DemoNLPModel()
