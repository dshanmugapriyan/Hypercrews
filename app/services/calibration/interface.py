from abc import ABC,abstractmethod
from dataclasses import dataclass
@dataclass
class CalibrationResult:
    calibrated_probability:float; confidence_score:float; is_calibrated:bool
class Calibrator(ABC):
    @abstractmethod
    def calibrate(self,raw_probability:float,evidence_count:int)->CalibrationResult: raise NotImplementedError
