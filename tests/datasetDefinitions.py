import pathlib as pl


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
