import abc
import os
import traceback
import typing
from glob import glob

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
    def measurements(self) -> typing.Iterable[ITOMeasurement]:
        pass


class DateMeasurementLoader(AbstractMeasurementLoader):
    _SETTINGS = settings
    _DATETIMEFORMAT = "%m_%d_%Y"
    def __init__(self, directory: str, templateDirectory: str):
        self._template = ITOMeasurement(templateDirectory, self._SETTINGS)
        self._measurements = []
        for f in glob(os.path.join(directory, '*')):
            if os.path.isdir(f):
                try:
                    self._measurements.append(ITOMeasurement(f, self._SETTINGS))
                except Exception as e:
                    print(f"Failed to load measurement at directory {f}")
                    print(traceback.print_exc())

        self._measurements = tuple(self._measurements)

    def template(self) -> ITOMeasurement:
        return self._template

    def measurements(self) -> typing.Iterable[ITOMeasurement]:
        return self._measurements