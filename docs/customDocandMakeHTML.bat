@ECHO OFF

sphinx-apidoc -f -o source ../src/pwspy
make.bat html

pause