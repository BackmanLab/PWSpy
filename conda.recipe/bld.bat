%PYTHON% setup.py install --single-version-externally-managed --record=record.txt

if errorlevel 1 exit 1

set MENU_DIR=%PREFIX%\Menu
IF NOT EXIST (%MENU_DIR%) mkdir %MENU_DIR%

copy %SRC_DIR%\src\pwspy\apps\PWSAnalysisApp\_resources\cellLogo.ico %MENU_DIR%\
if errorlevel 1 exit 1
copy %RECIPE_DIR%\menu-windows.json %MENU_DIR%\pwspy_shortcut.json
if errorlevel 1 exit 1
