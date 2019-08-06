set env=test

set root=%userprofile%\Anaconda3

call "%root%\Scripts\activate.bat" "%root%"

call conda activate %env%

set "currDir=%cd%"

call conda install -c file:///%currDir% -c defaults -c conda-forge pwspy --force-reinstall

pause