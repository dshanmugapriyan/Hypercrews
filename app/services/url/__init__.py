def get_url_model(is_demo: bool = True):
    from app.core.config import settings
    if settings.FORCE_DEMO_MODE or is_demo:
        from app.services.url.demo import DemoURLRiskModel
        return DemoURLRiskModel()
    else:
        from app.services.url.real import RealURLRiskModel
        return RealURLRiskModel()
