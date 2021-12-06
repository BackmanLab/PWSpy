import pathlib as pl
import pwspy.dataTypes as pwsdt
import pytest


testDataPath = pl.Path(__file__).parent / 'resources' / 'test_data'  # The path to find the test data in.


class Dataset:
    """
    Just a simple class to represent what is needed from a single test dataset.
    """
    datasetPath: pl.Path   # The path to the folder containing all the acquisitions
    referenceCellPath: pl.Path  # The path to the acquisition folder that is to be used as the reference for analysis.

    def __init__(self, datasetPath: pl.Path, referenceCellPath: pl.Path):
        self.datasetPath = datasetPath
        self.referenceCellPath = referenceCellPath

    def clean(self):
        """
        When starting the tests we don't need any analysis files which take a lot of space.
        go through and delete all analysis files.
        """
        acqs = [pwsdt.Acquisition(i) for i in self.datasetPath.glob("Cell[0-9]")]
        for acq in acqs:
            if acq.pws:
                for anName in acq.pws.getAnalyses():
                    acq.pws.removeAnalysis(anName)
                    print(f"Deleted {acq.filePath} PWS {anName}")
            if acq.dynamics:
                for anName in acq.dynamics.getAnalyses():
                    acq.dynamics.removeAnalysis(anName)
                    print(f"Deleted {acq.filePath} Dynamics {anName}")


@pytest.fixture(scope='session')
def sequenceData() -> Dataset:
    """A reference to the dataset with PWS data collected with the automated event sequencing plugin. Cleans out analysis files when done."""
    ds = Dataset(
        testDataPath / 'sequencer',
        testDataPath / 'sequencer' / "Cell3"
    )
    yield ds
    ds.clean()


@pytest.fixture(scope='session')
def dynamicsData() -> Dataset:
    """A reference to the dataset with PWS and Dynamics data. Cleans out analysis files when done."""
    ds = Dataset(
        testDataPath / 'dynamics',
        testDataPath / 'dynamics' / "Cell999"
    )
    yield ds
    ds.clean()
