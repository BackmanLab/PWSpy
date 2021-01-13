import abc
import os
import traceback
import typing
from glob import glob
import pwspy.dataTypes as pwsdt
from pwspy.analysis import pws as pwsAnalysis
from pwspy.apps.CalibrationSuite.ITOMeasurement import ITOMeasurement

settings = pwsAnalysis.PWSAnalysisSettings.loadDefaultSettings("Recommended")


class AbstractMeasurementLoader(abc.ABC):
    """
    In charge of loading ITO measurements from a folder structure. Multiple classes of this type could be made to support loading from
    different folder organization schemes.
    """
    @property
    @abc.abstractmethod
    def template(self) -> ITOMeasurement:
        pass

    @property
    @abc.abstractmethod
    def measurements(self) -> typing.Sequence[ITOMeasurement]:
        pass


class DateMeasurementLoader(AbstractMeasurementLoader):
    """
    This loader assumes that the data for a single measurement (ITO acquisition with and reference acquisition) are stored together in a folder that is named
    with a date of format {Month}_{Day}_{Year}
    """
    _SETTINGS = settings
    _DATETIMEFORMAT = "%m_%d_%Y"

    def __init__(self, directory: str, templateDirectory: str):
        self._template = self.loadMeasurement(templateDirectory)
        self._measurements = []
        for f in glob(os.path.join(directory, '*')):
            if os.path.isdir(f):
                try:
                    self._measurements.append(self.loadMeasurement(f))
                except:
                    print(f"Failed to load measurement at directory {f}")
                    print(traceback.print_exc())

        self._measurements = tuple(self._measurements)

    @classmethod
    def loadMeasurement(cls, directory: str) -> ITOMeasurement:
        """Load an ITO measurement assuming that `directory` contains and ITO acquisition numbered less than "Cell900" and
        a reference acquisition of water that is numbered greater than "Cell900". The ITOMeasurement will be named by the name of the enclosing folder."""
        acqs = [pwsdt.AcqDir(f) for f in glob(os.path.join(directory, "Cell*"))]
        itoAcq = [acq for acq in acqs if acq.getNumber() < 900]
        assert len(itoAcq) == 1, "There must be one and only one ITO film acquisition. Cell number should be less than 900."
        itoAcq = itoAcq[0]
        refAcq = [acq for acq in acqs if acq.getNumber() > 900]
        assert len(refAcq) == 1, "There must be one and only one reference acquisition. Cell number should be greater than 900."
        refAcq = refAcq[0]
        return ITOMeasurement(directory, itoAcq, refAcq, cls._SETTINGS, os.path.basename(directory))



    @property
    def template(self) -> ITOMeasurement:
        return self._template

    @property
    def measurements(self) -> typing.Iterable[ITOMeasurement]:
        return self._measurements
