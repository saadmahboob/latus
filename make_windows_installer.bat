REM for PyQt
mkdir dist\platforms
copy /Y C:\Python34\Lib\site-packages\PyQt5\plugins\platforms\*.dll dist\platforms
mkdir dist\icons
copy /Y icons\*.ico dist\icons
c:\python34\python.exe setup.py py2exe
"C:\Program Files (x86)\NSIS\makensis.exe" latus.nsi
