import os
import math
import joblib
from app.services.calibration.interface import CalibrationResult, Calibrator

class RealCalibrator(Calibrator):
    def __init__(self, model_dir="app/resources"):
        self.model_path = os.path.join(model_dir, "calibrator.joblib")
        self.isotonic_reg = None
        self._load_calibrator()

    def _load_calibrator(self):
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.isotonic_reg = data["calibrator"]
                print("Loaded Isotonic Regression calibrator successfully.")
            except Exception as e:
                print(f"Error loading calibrator: {e}")

    def calibrate(self, raw_probability: float, evidence_count: int) -> CalibrationResult:
        # If there's no evidence, we can't reliably confirm anything, so calibrate probability down
        if evidence_count == 0:
            return CalibrationResult(
                calibrated_probability=0.0,
                confidence_score=0.0,
                is_calibrated=True
            )

        # Try Isotonic Regression prediction
        if self.isotonic_reg:
            try:
                # IsotonicRegression expects a list-like input
                calibrated_prob = float(self.isotonic_reg.predict([raw_probability])[0])
                # Ensure boundary safety
                calibrated_prob = max(0.01, min(0.99, calibrated_prob))
            except Exception:
                # Platt calibration fallback
                calibrated_prob = self._platt_calibrate(raw_probability)
        else:
            # Platt calibration alternative
            calibrated_prob = self._platt_calibrate(raw_probability)

        # Confidence score calculation (represents evidence/model reliability, not probability)
        # Base confidence of 45%, adding 12% per evidence item, capped at 97%
        confidence = min(0.97, 0.45 + (0.12 * evidence_count))
        
        return CalibrationResult(
            calibrated_probability=round(calibrated_prob, 4),
            confidence_score=round(confidence, 4),
            is_calibrated=True
        )

    def _platt_calibrate(self, p: float) -> float:
        p = max(0.01, min(0.99, p))
        x = 5.5 * (p - 0.5)
        calibrated_prob = 1.0 / (1.0 + math.exp(-x))
        return calibrated_prob

def get_calibrator():
    return RealCalibrator()
