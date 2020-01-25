# -*- mode: python ; coding: utf-8 -*-

block_cipher = None
from os.path import join
import os

srcDir = '..\\..\\src\\pwspy'

#TODO update the _version file

a = Analysis(['PyInstallerAnalysisScript.py'],
             pathex=['../../src'],
             binaries=[],
             datas=[
                (join(srcDir, 'utility/reflection/refractiveIndexFiles/*'), 'pwspy/utility/reflection/refractiveIndexFiles'),
                (join(srcDir, 'utility/thinFilmInterferenceFiles/*'), 'pwspy/utility/thinFilmInterferenceFiles'),
                (join(srcDir, 'apps/_resources/*'), 'pwspy/apps/_resources'),
                (join(srcDir, 'analysis/_resources/defaultAnalysisSettings/*'), 'pwspy/analysis/_resources/defaultAnalysisSettings'),
                (join(srcDir, 'apps/PWSAnalysisApp/_resources/*'), 'pwspy/apps/PWSAnalysisApp/_resources'),
                (join(srcDir, 'dataTypes/jsonSchemas/*'), 'pwspy/dataTypes/jsonSchemas'),
                (join(srcDir, '_version'), 'pwspy')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='PWS Analysis App',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          icon = join(srcDir, 'apps/PWSAnalysisApp/_resources/cellLogo.ico'))
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='PWS Analysis App')
