set env=pwspy ::This should be the name of the Conda environment you want to install to. This environment needs to have already been created.

set root=%userprofile%\Anaconda3 ::We assume anaconda is installed in the default location

call "%root%\Scripts\activate.bat" "%root%" ::Call anaconda's script to activate the CMD environment

call conda activate %env% ::Activate the conda env.

set currDir=%cd%

if errorlevel 1 (
	echo Please create a Conda environment named %env%
) else (
	call conda install -c file:///%currDir% -c defaults -c conda-forge pwspy --force-reinstall ::Install the pwspy package from the current directory.
)

pause