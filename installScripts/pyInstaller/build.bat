:: This should be the name of the Conda environment you use for development of pwspython. This environment should have everything needed already installed.
set env=pwspy

:: We assume anaconda is installed in the default location
set root=%userprofile%\Anaconda3

:: Call anaconda's script to activate the CMD environment
call "%root%\Scripts\activate.bat" "%root%"

:: Activate the conda env.
call conda activate %env%

set currDir=%cd%

if errorlevel 1 (
	echo Please create a Conda environment named %env%
) else (
:: Install the pwspy package from the current directory.
	call pyinstaller PyInstallerAnalysisScript.spec
)

pause