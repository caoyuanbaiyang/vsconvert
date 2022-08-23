# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['D:\\PyCharmProject\\vsconvert\\main.py'],
             pathex=['C:\\Users\\tangy\\AppData\\Local\\Programs\\Python\\Python39\\Lib', 'C:\\Users\\tangy\\AppData\\Local\\Programs\\Python\\Python39\\libs', 'D:\\PyCharmProject\\vsconvert\\venv\\Lib\\site-packages', 'D:\\PyCharmProject\\vsconvert'],
             binaries=[],
             datas=[],
             hiddenimports=['model.vsc.vsc','lib.replace_lib','model.vscs.vscs','model.randpwd.randpwd'],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='vsconvert',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
