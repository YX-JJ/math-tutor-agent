Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

CurrentDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = CurrentDir

pythonExe = CurrentDir & "\python_portable\python.exe"
scriptPath = CurrentDir & "\background_server.py"

WshShell.Run """" & pythonExe & """ """ & scriptPath & """ fixed", 0, False
