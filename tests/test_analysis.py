from pwspy import analysis
import pwspy.dataTypes as pwsdt
from pwspy.utility.reflection import Material
import pytest
from conftest import testDataPath
import numpy as np

_analysisName = 'testAnalysis'

erMeta = pwsdt.ERMetaData.fromHdfFile(testDataPath / 'extraReflection', 'LCPWS2_100xpfs-8_4_2021')


class TestAnalysis:
    """
    Test the code under pwspy.analysis
    """

    @pytest.mark.parametrize('extraReflection', [None, erMeta])
    def test_pws_analysis(self, dynamicsData, extraReflection):
        """Test that PWS data can be analyzed. Results can be loaded. TODO check that values of analysis results don't change."""
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
        """Test that dynamics data can be analyzed, results can be loaded"""
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
            acq.dynamics.saveAnalysis(results, _analysisName)  # The analysis already exists so an OSError should be thrown.

        result = acq.dynamics.loadAnalysis(_analysisName)

        assert isinstance(result.rms_t_squared, np.ndarray)
        assert isinstance(result.meanReflectance, np.ndarray)
        assert isinstance(result.reflectance, pwsdt.DynCube)

    def test_compilation(self, dynamicsData):
        """Test that ROIs and PWS/Dynamics analysis results can be successfully `compiled` into a data table."""
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
                       pwsComp.run(acq.pws.loadAnalysis(_analysisName), roi.getRoi()),
                       dynComp.run(acq.dynamics.loadAnalysis(_analysisName), roi.getRoi())))

            print(f"Successfully Compiled {len(results)} ROIs for general, PWS, and dynamics analysis.")


