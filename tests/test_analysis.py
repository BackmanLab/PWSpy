import sys
import os
# sys.path.append(os.path.join('..', 'src'))

from pwspy import analysis
import pwspy.dataTypes as pwsdt
from pwspy.utility.reflection import Material
import pytest

#Import pytest fixtures.
# from datasetDefinitions import dynamicsData, sequenceData

_analysisName = 'testAnalysis'


class TestAnalysis:
    def test_pws_analysis(self, dynamicsData):
        settings = analysis.pws.PWSAnalysisSettings.loadDefaultSettings("Recommended")
        er = None  # TODO add other cases

        refAcq = pwsdt.Acquisition(dynamicsData.referenceCellPath)
        ref = refAcq.pws.toDataClass()  # TODO Test other cases of processing status (exposure normalized or not)
        anls = analysis.pws.PWSAnalysis(settings=settings, extraReflectance=er, ref=ref)

        acq = pwsdt.Acquisition(dynamicsData.datasetPath / "Cell1")
        cube = acq.pws.toDataClass()  # TODO test various states of preprocessing
        results, warnings = anls.run(cube)

        acq.pws.saveAnalysis(results, _analysisName, overwrite=True)
        with pytest.raises(OSError):
            acq.pws.saveAnalysis(results, _analysisName)  # The analysis already exists so an OSError should be thrown.

        acq.pws.loadAnalysis(_analysisName)

        # TODO add assertions

    def test_dynamics_analysis(self, dynamicsData):
        er = None  # TODO add other cases

        settings = analysis.dynamics.DynamicsAnalysisSettings(
            cameraCorrection=None,
            extraReflectanceId=er.idTag if er is not None else None,
            referenceMaterial=Material.Water,
            numericalAperture=0.52,
            relativeUnits=True
        )

        refAcq = pwsdt.Acquisition(dynamicsData.referenceCellPath)
        ref = refAcq.dynamics.toDataClass()  # TODO Test other cases of processing status (exposure normalized or not)
        anls = analysis.dynamics.DynamicsAnalysis(settings=settings, extraReflectance=er, ref=ref)

        acq = pwsdt.Acquisition(dynamicsData.datasetPath / 'Cell1')
        cube = acq.dynamics.toDataClass()  # TODO test various states of preprocessing
        results, warnings = anls.run(cube)

        acq.dynamics.saveAnalysis(results, _analysisName)

        acq.dynamics.loadAnalysis(_analysisName)

    def test_compilation(self, dynamicsData):
        settings = analysis.compilation.GenericCompilerSettings(True)
        genComp = analysis.compilation.GenericRoiCompiler(settings)

        settings = analysis.compilation.PWSCompilerSettings(True, True, True)
        pwsComp = analysis.compilation.PWSRoiCompiler(settings)

        settings = analysis.compilation.DynamicsCompilerSettings(True, True, True)
        dynComp = analysis.compilation.DynamicsRoiCompiler(settings)

        acq = pwsdt.Acquisition(dynamicsData.datasetPath / 'Cell1')

        for roiSpecs in acq.getRois():
            roi = acq.loadRoi(*roiSpecs)
            results = (genComp.run(roi),
                       pwsComp.run(acq.pws.loadAnalysis(_analysisName), roi),
                       dynComp.run(acq.dynamics.loadAnalysis(_analysisName), roi))
            print(results)


class TestSequence:
    def test_sequence(self, sequenceData):
        from pwspy.utility.acquisition import loadDirectory
        seq, acqs = loadDirectory(sequenceData.datasetPath)


