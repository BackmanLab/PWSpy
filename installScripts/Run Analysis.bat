set env=pwspy

set root=%userprofile%\Anaconda3

call "%root%\Scripts\activate.bat" "%root%"

call conda activate %env%

if errorlevel 1 (
	echo Please create a Conda environment named %env% and reinstall the PWS software
) else (
	call python -m pwspy.apps.PWSAnalysisApp
)

pause
