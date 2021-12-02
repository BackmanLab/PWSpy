# Copyright 2018-2021 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

"""
This script loads analysis results from a list of PWS acquisitions and uses the "PWSRoiCompiler" class to get average output
values within the ROIs for each acquisition. The compiled results are then placed into a Pandas dataframe.
"""
import pandas
from pwspy.analysis.compilation import PWSRoiCompiler, PWSCompilerSettings
from examples import PWSExperimentPath
import pwspy.dataTypes as pwsdt

tmpList = []
compiler = PWSRoiCompiler(PWSCompilerSettings(reflectance=True, rms=True))

listOfAcquisitions = [pwsdt.Acquisition(i) for i in PWSExperimentPath.glob("Cell[0-9]")]
for acquisition in listOfAcquisitions:
    for analysisName in acquisition.pws.getAnalyses():
        analysisResults = acquisition.pws.loadAnalysis(analysisName)
        for roiSpec in acquisition.getRois():
            roiFile = acquisition.loadRoi(*roiSpec)
            results, warnings = compiler.run(analysisResults, roiFile.getRoi())

            if len(warnings) > 0:
                print(warnings)

            tmpList.append(dict(
                acquisition=acquisition,
                cellNumber=acquisition.getNumber(),
                analysisResults=analysisResults,
                rms=results.rms,
                reflectance=results.reflectance,
                roiNum=roiFile.number,
                roiName=roiFile.name
            ))

dataFrame = pandas.DataFrame(tmpList)
print(dataFrame)
