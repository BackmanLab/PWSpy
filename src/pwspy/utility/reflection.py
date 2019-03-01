from pwspy import ImCube
from pwspy.utility import reflectanceHelper
import itertools
import matplotlib.pyplot as plt
import numpy as np
from functools import reduce


def _interpolateNans(arr):
    def interp1(arr1):
        nans = np.isnan(arr1)
        f = lambda z: z.nonzero()[0]
        arr1[nans] = np.interp(f(nans), f(~nans), arr1[~nans])
        return arr1

    arr = np.apply_along_axis(interp1, 2, arr)
    return arr


def plotExtraReflection(cubes: list, selectMaskUsingSetting: str = None, plotReflectionImages: bool = False,
                        excludedCombos: list = []):
    """Expects a list of ImCubes which each has a `material` property matching one of the materials in the `ReflectanceHelper` module and a
    `setting` property labeling how the microscope was set up for this image.
    """
    # Error checking
    assert isinstance(cubes[0], ImCube)
    assert hasattr(cubes[0], 'material')
    assert hasattr(cubes[0], 'setting')

    if selectMaskUsingSetting is None:
        mask = cubes
    else:
        mask = [i for i in cubes if (i.setting == selectMaskUsingSetting)]
    print("Select an ROI")
    mask = mask[0].selectLassoROI()  # Select an ROI to analyze

    # load theory reflectance
    theoryR = {}  # Theoretical reflectances
    materials = set([i.material for i in cubes])
    for material in materials:  # For each unique material in the `cubes` list
        theoryR[material] = reflectanceHelper.getReflectance(material, 'glass', index=cubes[0].wavelengths)

    matCombos = list(itertools.combinations(materials, 2))  # All the combinations of materials that can be compared
    matCombos = [(m1, m2) for m1, m2 in matCombos if
                 not (((m1, m2) in excludedCombos) or ((m2, m1) in excludedCombos))]  # Remove excluded combinations.
    for i, (m1, m2) in enumerate(
            matCombos):  # Make sure to arrange materials so that our reflectance ratio is greater than 1
        if (reflectanceHelper.getReflectance(m1, 'glass') / reflectanceHelper.getReflectance(m2, 'glass')).mean() < 1:
            matCombos[i] = (m2, m1)
    settings = set([i.setting for i in cubes])  # Unique setting values
    allCombos = {}
    for sett in settings:
        allCombos[sett] = {}
        for matCombo in matCombos:
            matCubes = {material: [cube for cube in cubes if ((cube.material == material) and (cube.setting == sett))]
                        for material in matCombo}  # The imcubes relevant to this loop.
            allCombos[sett][matCombo] = [{'cubes': dict(zip(matCubes.keys(), combo))} for combo in
                                         itertools.product(*matCubes.values())]

    meanValues = {}
    params = ['rextra', 'I0', 'mat1Spectra', 'mat2Spectra', 'cFactor']
    for sett in settings:
        meanValues[sett] = {}
        for matCombo in matCombos:
            for combo in allCombos[sett][matCombo]:
                cubes = combo['cubes']
                mat1, mat2 = cubes.keys()
                combo['mat1Spectra'] = cubes[mat1].getMeanSpectra(mask)[0]
                combo['mat2Spectra'] = cubes[mat2].getMeanSpectra(mask)[0]
                combo['rextra'] = ((theoryR[mat1] * combo['mat2Spectra']) - (theoryR[mat2] * combo['mat1Spectra'])) / (
                            combo['mat1Spectra'] - combo['mat2Spectra'])
                combo['I0'] = combo['mat2Spectra'] / (theoryR[mat2] + combo['rextra'])
                combo['cFactor'] = (combo['rextra'].mean() + theoryR['water'].mean()) / theoryR['water'].mean()
            meanValues[sett][matCombo] = {
            param: np.array(list([combo[param] for combo in allCombos[sett][matCombo]])).mean(axis=0) for param in
            params}
        meanValues[sett]['mean'] = {
        param: np.array(list([meanValues[sett][matCombo][param] for matCombo in matCombos])).mean(axis=0) for param in
        params}

    # plot
    fig, ax = plt.subplots()  # For extra reflections
    fig.suptitle("Extra Reflection")
    ax.set_ylabel("%")
    ax.set_xlabel("nm")
    for sett in settings:
        for matCombo in matCombos:
            mat1, mat2 = matCombo
            for combo in allCombos[sett][matCombo]:
                cubes = combo['cubes']
                ax.plot(cubes[mat1].wavelengths, combo['rextra'],
                        label=f'{sett} {mat1}:{int(cubes[mat1].exposure)}ms {mat2}:{int(cubes[mat2].exposure)}ms')
        ax.plot(cubes[mat1].wavelengths, meanValues[sett]['mean']['rextra'], color='k', label=f'{sett} mean')
    ax.legend()

    fig2, ratioAxes = plt.subplots(nrows=len(matCombos))  # for correction factor
    if not isinstance(ratioAxes, np.ndarray): ratioAxes = np.array(ratioAxes).reshape(
        1)  # If there is only one axis we still want it to be a list for the rest of the code
    ratioAxes = dict(zip(matCombos, ratioAxes))
    for combo in matCombos:
        ratioAxes[combo].set_title(f'{combo[0]}/{combo[1]} reflection ratio')
        ratioAxes[combo].plot(theoryR[combo[0]] / theoryR[combo[1]], label='Theory')
    for sett in settings:
        for matCombo in matCombos:
            mat1, mat2 = matCombo
            for combo in allCombos[sett][matCombo]:
                cubes = combo['cubes']
                ratioAxes[matCombo].plot(cubes[mat1].wavelengths, combo['mat1Spectra'] / combo['mat2Spectra'],
                                         label=f'{sett} {mat1}:{int(cubes[mat1].exposure)}ms {mat2}:{int(
                                             cubes[mat2].exposure)}ms')
    [ratioAxes[combo].legend() for combo in matCombos]

    for sett in settings:
        means = meanValues[sett]['mean']

        fig3, scatterAx = plt.subplots()  # A scatter plot of the theoretical vs observed reflectance ratio.
        scatterAx.set_ylabel("Theoretical Ratio")
        scatterAx.set_xlabel("Observed Ratio w/ cFactor")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in matCombos]
        scatterPointsX = [means['cFactor'] * (
                    meanValues[sett][matCombo]['mat1Spectra'] / meanValues[sett][matCombo]['mat2Spectra']).mean() for
                          matCombo in matCombos]
        [scatterAx.scatter(x, y, label=f'{matCombo[0]}/{matCombo[1]}') for x, y, matCombo in
         zip(scatterPointsX, scatterPointsY, matCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx.plot(x, x, label='1:1')
        scatterAx.legend()

        fig4, scatterAx2 = plt.subplots()  # A scatter plot of the theoretical vs observed reflectance ratio.
        scatterAx2.set_ylabel("Theoretical Ratio")
        scatterAx2.set_xlabel("Observed Ratio after Subtraction")
        scatterPointsY = [(theoryR[matCombo[0]] / theoryR[matCombo[1]]).mean() for matCombo in matCombos]
        scatterPointsX = [((meanValues[sett][matCombo]['mat1Spectra'] - means['I0'] * means['rextra']) / (
                    meanValues[sett][matCombo]['mat2Spectra'] - means['I0'] * means['rextra'])).mean() for matCombo in
                          matCombos]
        [scatterAx2.scatter(x, y, label=f'{matCombo[0]}/{matCombo[1]}') for x, y, matCombo in
         zip(scatterPointsX, scatterPointsY, matCombos)]
        x = np.array([0, max(scatterPointsX)])
        scatterAx2.plot(x, x, label='1:1')
        scatterAx2.legend()

        if plotReflectionImages:
            for matCombo in matCombos:
                mat1, mat2 = matCombo
                for combo in allCombos[sett][matCombo]:
                    cubes = combo['cubes']
                    plt.figure()
                    plt.title(f"Reflectance %. {sett}, {mat1}:{int(cubes[mat2].exposure)}ms, {mat2}:{int(
                        cubes[mat2].exposure)}ms")
                    _ = ((theoryR[mat1][np.newaxis, np.newaxis, :] * cubes[mat2].data) - (
                                theoryR[mat2][np.newaxis, np.newaxis, :] * cubes[mat1].data)) / (
                                    cubes[mat1].data - cubes[mat2].data)
                    _[np.isinf(_)] = np.nan
                    if np.any(np.isnan(_)):
                        _ = _interpolateNans(
                            _)  # any division error resulting in an inf will really mess up our refIm. so we interpolate them out.
                    refIm = _.mean(axis=2)
                    plt.imshow(refIm, vmin=np.percentile(refIm, .5), vmax=np.percentile(refIm, 99.5))
                    plt.colorbar()

        print(f"{sett} correction factor")
        print(means['cFactor'])
    return meanValues, allCombos


def saveRExtra(cubes: list, excludedCombos: list = []):
    """Expects a list of ImCubes which each has a `material` property matching one of the materials in the `ReflectanceHelper` module."""
    # Error checking
    assert isinstance(cubes[0], ImCube)
    assert hasattr(cubes[0], 'material')

    # load theory reflectance
    theoryR = {}  # Theoretical reflectances
    materials = set([i.material for i in cubes])
    avgdCubes = {}
    for material in materials:  # For each unique material in the `cubes` list
        print("Averaging cubes for: ", material)
        theoryR[material] = reflectanceHelper.getReflectance(material, 'glass', index=cubes[
            0].wavelengths)  # save the theoretical reflectance
        _ = [i for i in cubes if i.material == material]  # average all cubes of the same material
        avgdCubes[material] = (reduce(lambda x, y: x + y, _) / len(_))

    matCombos = list(itertools.combinations(materials, 2))  # All the combinations of materials that can be compared
    matCombos = [(m1, m2) for m1, m2 in matCombos if
                 not (((m1, m2) in excludedCombos) or ((m2, m1) in excludedCombos))]  # Remove excluded combinations.

    allCombos = {}
    for matCombo in matCombos:
        matCubes = {material: avgdCubes[material] for material in matCombo}  # The imcubes relevant to this loop.
        allCombos[matCombo] = matCubes
    del avgdCubes

    rExtra = {}
    for matCombo in matCombos:
        print("Calculating RExtra for: ", matCombo)
        combo = allCombos[matCombo]
        mat1, mat2 = combo.keys()
        rExtra[matCombo] = ((np.array(theoryR[mat1][np.newaxis, np.newaxis, :]) * combo[mat2].data) - (
                    np.array(theoryR[mat2][np.newaxis, np.newaxis, :]) * combo[mat1].data)) / (
                                       combo[mat1].data - combo[mat2].data)
        del allCombos[matCombo]
        rExtra[matCombo][np.isinf(rExtra[matCombo])] = np.nan
        nans = np.isnan(rExtra[matCombo]).sum()
        if nans > 0:
            print(nans, " invalid values detected in " + str(matCombo) + ". Interpolating.")
            rExtra[matCombo] = _interpolateNans(rExtra[
                                                    matCombo])  # any division error resulting in an inf will really mess up our refIm. so we interpolate them out.

    _ = [rExtra[matCombo] for matCombo in matCombos]
    rExtra['mean'] = reduce(lambda x, y: x + y, _) / len(_)
    return rExtra
