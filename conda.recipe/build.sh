#!/bin/bash

$PYTHON setup.py install --single-version-externally-managed --record=record.txt

MENU_DIR = $PREFIX\Menu
echo $MENU_DIR
if [! -d "$MENU_DIR"]
then
  mkdir $MENU_DIR

cp "$SRC_DIR\src\pwspy\apps\PWSAnalysisApp\_resources\cellLogo.ico" "$MENU_DIR"
cp "$RECIPE_DIR\menu-windows.json" "$MENU_DIR\pwspy_shortcut.json"
