def get_fusion_model(is_demo: bool = True):
    from app.core.config import settings
    if settings.FORCE_DEMO_MODE or is_demo:
        from app.services.fusion.demo import DemoFusionModel
        return DemoFusionModel()
    else:
        from app.services.fusion.real import RealFusionModel
        return RealFusionModel()
