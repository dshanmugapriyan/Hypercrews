from app.services.calibration.interface import CalibrationResult,Calibrator
class PassthroughCalibrator(Calibrator):
    def calibrate(self,raw_probability,evidence_count):
        return CalibrationResult(round(raw_probability,4),round(min(.75,.15+.1*evidence_count),4),False)
def get_calibrator(): return PassthroughCalibrator()
