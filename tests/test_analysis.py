import sys
import os
# sys.path.append(os.path.join('..', 'src'))

from pwspy import analysis
import pwspy.dataTypes as pwsdt
from pwspy.utility.reflection import Material
import pytest

_analysisName = 'testAnalysis'
resourcesDir = os.path.join(os.path.split(__file__)[0], 'resources')
_acqDir = os.path.join(resourcesDir, 'seqTest', 'Cell1')
_refDir = os.path.join(resourcesDir, 'seqTest', 'Cell3')


def test_pws_analysis():
    settings = analysis.pws.PWSAnalysisSettings.loadDefaultSettings("Recommended")
    er = None  # TODO add other cases
    
    refAcq = pwsdt.AcqDir(_refDir)
    ref = refAcq.pws.toDataClass()  # TODO Test other cases of processing status (exposure normalized or not)
    anls = analysis.pws.PWSAnalysis(settings=settings, extraReflectance=er, ref=ref)
    
    acq = pwsdt.AcqDir(_acqDir)
    cube = acq.pws.toDataClass()  # TODO test various states of preprocessing
    results, warnings = anls.run(cube)

    with pytest.raises(OSError):
        acq.pws.saveAnalysis(results, _analysisName)  # The analysis already exists so an OSError should be thrown.
    acq.pws.saveAnalysis(results, _analysisName, overwrite=True)
    
    acq.pws.loadAnalysis(_analysisName)
    
    # TODO add assertions
    
def test_dynamics_analysis():
    er = None  # TODO add other cases

    settings = analysis.dynamics.DynamicsAnalysisSettings(
        cameraCorrection=None,
        extraReflectanceId=er.idTag if er is not None else None,
        referenceMaterial=Material.Water,
        numericalAperture=0.52,
        relativeUnits=True
    )

    refAcq = pwsdt.AcqDir(_refDir)
    ref = refAcq.dynamics.toDataClass()  # TODO Test other cases of processing status (exposure normalized or not)
    anls = analysis.dynamics.DynamicsAnalysis(settings=settings, extraReflectance=er, ref=ref)

    acq = pwsdt.AcqDir(_acqDir)
    cube = acq.dynamics.toDataClass()  # TODO test various states of preprocessing
    results, warnings = anls.run(cube)

    acq.dynamics.saveAnalysis(results, _analysisName)

    acq.dynamics.loadAnalysis(_analysisName)


def test_compilation():
    settings = analysis.compilation.GenericCompilerSettings(True)
    genComp = analysis.compilation.GenericRoiCompiler(settings)
    
    settings = analysis.compilation.PWSCompilerSettings(True, True, True)
    pwsComp = analysis.compilation.PWSRoiCompiler(settings)
    
    settings = analysis.compilation.DynamicsCompilerSettings(True, True, True)
    dynComp = analysis.compilation.DynamicsRoiCompiler(settings)
    
    acq = pwsdt.AcqDir(_acqDir)
    
    for roiSpecs in acq.getRois():
        roi = acq.loadRoi(*roiSpecs)
        results = (genComp.run(roi), 
                   pwsComp.run(acq.pws.loadAnalysis(_analysisName), roi),
                   dynComp.run(acq.dynamics.loadAnalysis(_analysisName), roi))
        print(results)


def test_sequence():
    from pwspy.utility.acquisition import loadDirectory
    seq, acqs = loadDirectory((os.path.join(resourcesDir, 'seqTest')))

if __name__ == '__main__':
    test_pws_analysis()
    a = 1