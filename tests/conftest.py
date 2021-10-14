import pathlib as pl
import typing as t_
import pwspy.dataTypes as pwsdt
import pytest

testDataPath = pl.Path(__file__).parent / 'resources' / 'test_data'


class Dataset:
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

# sequenceTestData = Dataset()
# sequenceTestData.datasetPath = testDataPath / 'sequencer'
# sequenceTestData.referenceCellPath = sequenceTestData.datasetPath / 'Cell3'
#
# dynamicsTestData = Dataset()
# dynamicsTestData.datasetPath = testDataPath / 'dynamics'
# dynamicsTestData.referenceCellPath = dynamicsTestData.datasetPath / 'Cell999'

# allDatasets: t_.Tuple[Dataset, ...] = (sequenceTestData, dynamicsTestData)


@pytest.fixture(scope='session')
def sequenceData() -> Dataset:
    ds = Dataset(
        testDataPath / 'sequencer',
        testDataPath / 'sequencer' / "Cell3"
    )
    yield ds
    ds.clean()


@pytest.fixture(scope='session')
def dynamicsData() -> Dataset:
    ds = Dataset(
        testDataPath / 'dynamics',
        testDataPath / 'dynamics' / "Cell999"
    )
    yield ds
    ds.clean()

# if __name__ == '__main__':
#     Dataset(
#         testDataPath / 'dynamics',
#         testDataPath / 'dynamics' / "Cell3"
#     ).clean()
#     a = 1