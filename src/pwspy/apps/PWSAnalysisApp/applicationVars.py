import os
from pwspy.apps import appPath
dataDirectory = os.path.join(appPath, 'PWSAnalysisData')
analysisSettingsDirectory = os.path.join(dataDirectory, 'AnalysisSettings')
extraReflectionDirectory = os.path.join(dataDirectory, 'ExtraReflection')
googleDriveAuthPath = os.path.join(dataDirectory, 'GoogleDrive')
