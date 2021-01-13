from pwspy.apps.CalibrationSuite.ITOMeasurement import ITOMeasurement
from pwspy.apps.CalibrationSuite.loaders import AbstractMeasurementLoader
import typing
import pwspy.analysis.pws as pwsAnalysis
import os
import pwspy.dataTypes as pwsdt


class Loader(AbstractMeasurementLoader):
    """
    An ITO calibration loader for this experiment. The reference for each ITO acquisiton is Cell3 from the same experiemental condition

    """
    analysisSettings = pwsAnalysis.PWSAnalysisSettings.loadDefaultSettings("Recommended")

    def __init__(self, rootDir: str, measurementSetName: str):
        meas = self.generateITOMeasurements(rootDir, measurementSetName)
        template = [m for m in meas if m.name == 'centered_0_52'][0]
        self._template = template
        self._measurements = meas

    @classmethod
    def generateITOMeasurements(cls, rootDir: str, measurementSetName: str):
        measurements = []
        for expType in ['centered', 'fieldstop', 'translation']:
            for condition in os.listdir(os.path.join(rootDir, expType)):
                if os.path.isdir(os.path.join(rootDir, expType, condition)):
                    itoAcq = pwsdt.AcqDir(os.path.join(rootDir, expType, condition, 'ito', 'Cell1'))
                    refAcq = pwsdt.AcqDir(os.path.join(rootDir, expType, condition, 'cells', "Cell3"))
                    name = f"{expType}_{condition}"
                    homeDir = os.path.join(rootDir, "calibrationResults", measurementSetName, name)
                    measurements.append(ITOMeasurement(homeDir, itoAcq, refAcq, cls.analysisSettings, name))
        return measurements

    @property
    def template(self) -> ITOMeasurement:
        return self._template

    @property
    def measurements(self) -> typing.Tuple[ITOMeasurement]:
        return tuple(self._measurements)
