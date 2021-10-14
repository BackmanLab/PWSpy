from pwspy.utility.acquisition import loadDirectory, PositionsStep
from pwspy.utility.micromanager import PositionList


class TestSequence:
    def test_sequence(self, sequenceData):
        seq, acqs = loadDirectory(sequenceData.datasetPath)

        seq.printSubTree()

        multiplePosStep: PositionsStep = [i for i in seq.iterateChildren() if isinstance(i, PositionsStep)][0]
        positionDict = multiplePosStep.settings['posList']
        posList = PositionList.fromDict(positionDict)

        assert len(posList) == len(acqs)

        for acq in acqs:
            iterationNum = acq.sequencerCoordinate.getStepIteration(multiplePosStep)
            print(posList[iterationNum])