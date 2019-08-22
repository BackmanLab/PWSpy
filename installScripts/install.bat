set env=pwspy

set root=%userprofile%\Anaconda3

call "%root%\Scripts\activate.bat" "%root%"

call conda activate %env%

set currDir=%cd%

if errorlevel 1 (
	echo Please create a Conda environment named %env%
) else (
	call conda install -c file:///%currDir% -c defaults -c conda-forge pwspy --force-reinstall
)

pause