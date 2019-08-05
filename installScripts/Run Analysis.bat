set env=test

set root=%userprofile%\Anaconda3

call "%root%\Scripts\activate.bat" "%root%"

call conda activate %env%

call python -m pwspy.apps.PWSAnalysisApp
