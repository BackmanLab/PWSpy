from pwspy.analysis.dynamics import DynamicsAnalysisSettings, DynamicsAnalysis
from pwspy.moduleConsts import Material

if __name__ == "__main__":
    import os.path as osp
    from pwspy.dataTypes.data import DynCube

    wDir = r"C:\Users\backman05\Desktop\Dynamics data\A1"
    cubeDir = osp.join(wDir, "Cell1\Dynamics")
    refDir = osp.join(wDir, "Cell997\Dynamics")

    settings = DynamicsAnalysisSettings(None, Material.Water, 0.5)
    ref = DynCube.fromTiff(refDir)
    ref.correctCameraEffects()
    cube = DynCube.fromTiff(cubeDir)
    cube.correctCameraEffects()
    an = DynamicsAnalysis(settings, ref, None)
    results, warns = an.run(cube)