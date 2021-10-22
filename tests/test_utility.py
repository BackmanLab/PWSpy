from pwspy.utility.acquisition import loadDirectory, PositionsStep
from pwspy.utility.micromanager import PositionList


class TestSequence:
    def test_sequence(self, sequenceData):
        """Test that the metadata files saved by the event sequencer plugin can be loaded. Use the sequence metadata to load acquisitions
        and a position list giving the locations of each acquisition. Test basic operations on the position list."""
        seq, acqs = loadDirectory(sequenceData.datasetPath)

        seq.printSubTree()

        multiplePosStep: PositionsStep = [i for i in seq.iterateChildren() if isinstance(i, PositionsStep)][0]
        positionDict = multiplePosStep.settings['posList']
        posList = PositionList.fromDict(positionDict)

        assert len(posList) == len(acqs)

        posList2 = posList.copy()
        posList2.mirrorX().mirrorY()  # inplace
        afTransform = posList.getAffineTransform(posList2)
        posList3 = posList.applyAffineTransform(afTransform)

        for acq in acqs:
            iterationNum = acq.sequencerCoordinate.getStepIteration(multiplePosStep)
            print(posList[iterationNum])
