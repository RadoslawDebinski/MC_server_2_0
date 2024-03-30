@echo off
rem Save the current working directory
pushd %CD%

rem Call the main Python script
%CD%\..\..\python\python main.py  --reset

rem Change back to the original working directory
popd

pause