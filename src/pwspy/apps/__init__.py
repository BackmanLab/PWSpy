import os
resources = os.path.join(os.path.split(__file__)[0], 'resources')
appPath = os.path.expanduser('~/PwspyApps')
if not os.path.exists(appPath):
    os.mkdir(appPath)
