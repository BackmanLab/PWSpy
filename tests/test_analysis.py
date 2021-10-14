import sys
import os
# sys.path.append(os.path.join('..', 'src'))

from pwspy import analysis
import pwspy.dataTypes as pwsdt
from pwspy.utility.reflection import Material
import pytest
from conftest import testDataPath
import numpy as np

_analysisName = 'testAnalysis'

erMeta = pwsdt.ERMetaData.fromHdfFile(testDataPath / 'extraReflection', 'LCPWS2_100xpfs-8_4_2021')


class TestAnalysis:
    @pytest.mark.parametrize('extraReflection', [None, erMeta])
    def test_pws_analysis(self, dynamicsData, extraReflection):
        settings = analysis.pws.PWSAnalysisSettings.loadDefaultSettings("Recommended")

        refAcq = pwsdt.Acquisition(dynamicsData.referenceCellPath)
        ref = refAcq.pws.toDataClass()
        anls = analysis.pws.PWSAnalysis(settings=settings, extraReflectance=extraReflection, ref=ref)

        acq = pwsdt.Acquisition(dynamicsData.datasetPath / "Cell1")
        cube = acq.pws.toDataClass()
        results, warnings = anls.run(cube)

        acq.pws.saveAnalysis(results, _analysisName, overwrite=True)
        with pytest.raises(OSError):
            acq.pws.saveAnalysis(results, _analysisName)  # The analysis already exists so an OSError should be thrown.

        result = acq.pws.loadAnalysis(_analysisName)

        assert isinstance(result.rms, np.ndarray)
        assert isinstance(result.meanReflectance, np.ndarray)
        assert isinstance(result.reflectance, pwsdt.KCube)

    @pytest.mark.parametrize('extraReflection', [None, erMeta])
    def test_dynamics_analysis(self, dynamicsData, extraReflection):

        settings = analysis.dynamics.DynamicsAnalysisSettings(
            cameraCorrection=None,
            extraReflectanceId=extraReflection.idTag if extraReflection is not None else None,
            referenceMaterial=Material.Water,
            numericalAperture=0.52,
            relativeUnits=True
        )

        refAcq = pwsdt.Acquisition(dynamicsData.referenceCellPath)
        ref = refAcq.dynamics.toDataClass()
        anls = analysis.dynamics.DynamicsAnalysis(settings=settings, extraReflectance=extraReflection, ref=ref)

        acq = pwsdt.Acquisition(dynamicsData.datasetPath / 'Cell1')
        cube = acq.dynamics.toDataClass()
        results, warnings = anls.run(cube)

        acq.dynamics.saveAnalysis(results, _analysisName, overwrite=True)
        with pytest.raises(OSError):
            acq.pws.saveAnalysis(results, _analysisName)  # The analysis already exists so an OSError should be thrown.

        result = acq.dynamics.loadAnalysis(_analysisName)

        assert isinstance(result.rms_t_squared, np.ndarray)
        assert isinstance(result.meanReflectance, np.ndarray)
        assert isinstance(result.reflectance, pwsdt.DynCube)

    def test_compilation(self, dynamicsData):
        settings = analysis.compilation.GenericCompilerSettings(roiArea=True)
        genComp = analysis.compilation.GenericRoiCompiler(settings)

        settings = analysis.compilation.PWSCompilerSettings(reflectance=True, rms=True, polynomialRms=True)
        pwsComp = analysis.compilation.PWSRoiCompiler(settings)

        settings = analysis.compilation.DynamicsCompilerSettings(meanReflectance=True, rms_t_squared=True, diffusion=True)
        dynComp = analysis.compilation.DynamicsRoiCompiler(settings)

        acq = pwsdt.Acquisition(dynamicsData.datasetPath / 'Cell1')

        results = []
        for roiSpecs in acq.getRois():
            roi = acq.loadRoi(*roiSpecs)
            results.append((genComp.run(roi),
                       pwsComp.run(acq.pws.loadAnalysis(_analysisName), roi),
                       dynComp.run(acq.dynamics.loadAnalysis(_analysisName), roi)))

            print(f"Successfully Compiled {len(results)} ROIs for general, PWS, and dynamics analysis.")


class TestSequence:
    def test_sequence(self, sequenceData):
        from pwspy.utility.acquisition import loadDirectory, PositionsStep
        from pwspy.utility.micromanager import PositionList
        seq, acqs = loadDirectory(sequenceData.datasetPath)

        seq.printSubTree()

        multiplePosStep: PositionsStep = [i for i in seq.iterateChildren() if isinstance(i, PositionsStep)][0]
        positionDict = multiplePosStep.settings['posList']
        posList = PositionList.fromDict(positionDict)

        assert len(posList) == len(acqs)

        for acq in acqs:
            iterationNum = acq.sequencerCoordinate.getStepIteration(multiplePosStep)
            print(posList[iterationNum])


