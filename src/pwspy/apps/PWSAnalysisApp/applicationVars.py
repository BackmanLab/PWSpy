import os
from pwspy.apps import appPath
dataDirectory = os.path.join(appPath, 'PWSAnalysisData')
analysisSettingsDirectory = os.path.join(dataDirectory, 'PWSAnalysisSettings')
extraReflectionDirectory = os.path.join(dataDirectory, 'ExtraReflection')
googleDriveAuthPath = os.path.join(dataDirectory, 'GoogleDrive')
