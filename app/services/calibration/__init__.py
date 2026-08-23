def get_calibrator(is_demo: bool = True):
    from app.core.config import settings
    if settings.FORCE_DEMO_MODE or is_demo:
        from app.services.calibration.demo import PassthroughCalibrator
        return PassthroughCalibrator()
    else:
        from app.services.calibration.real import RealCalibrator
        return RealCalibrator()
