import pathlib as pl
import typing as t_
import pwspy.dataTypes as pwsdt

testDataPath = pl.Path(__file__).parent / 'resources' / 'test_data'


class Dataset:
    datasetPath: pl.Path   # The path to the folder containing all the acquisitions
    referenceCellPath: pl.Path  # The path to the acquisition folder that is to be used as the reference for analysis.


sequenceTestData = Dataset()
sequenceTestData.datasetPath = testDataPath / 'sequencer'
sequenceTestData.referenceCellPath = sequenceTestData.datasetPath / 'Cell3'

dynamicsTestData = Dataset()
dynamicsTestData.datasetPath = testDataPath / 'dynamics'
dynamicsTestData.referenceCellPath = dynamicsTestData.datasetPath / 'Cell999'

allDatasets: t_.Tuple[Dataset, ...] = (sequenceTestData, dynamicsTestData)


def cleanDatasets():
    """When starting the tests we don't need any analysis files which take a lot of space. go through and delete all analysis files."""
    for dataset in allDatasets:
        acqs = [pwsdt.Acquisition(i) for i in dataset.datasetPath.glob("Cell[0-9]")]
        for acq in acqs:
            if acq.pws:
                for anName in acq.pws.getAnalyses():
                    acq.pws.removeAnalysis(anName)
                    print(f"Deleted {acq.filePath} PWS {anName}")
            if acq.dynamics:
                for anName in acq.dynamics.getAnalyses():
                    acq.dynamics.removeAnalysis(anName)
                    print(f"Deleted {acq.filePath} Dynamics {anName}")



if __name__ == '__main__':
    cleanDatasets()
