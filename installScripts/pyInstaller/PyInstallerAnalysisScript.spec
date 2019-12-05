# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['PyInstallerAnalysisScript.py'],
             pathex=['C:\\Users\\backman05\\Documents\\Bitbucket\\pwspython\\installScripts\\pyInstaller'],
             binaries=[],
             datas=[
                ('utility/reflection/refractiveIndexFiles/*', '.'),
                ('utility/thinFilmInterferenceFiles/*', '.'),
                ('apps/_resources/*', '.'),
                ('analysis/_resources/defaultAnalysisSettings/*', '.'),
                ('apps/PWSAnalysisApp/_resources/*', '.'),
                ('dataTypes/jsonSchemas/*', '.'),
                ('_version', '.')
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
          name='PyInstallerAnalysisScript',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='PyInstallerAnalysisScript')
