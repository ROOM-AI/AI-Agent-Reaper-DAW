' START_DEMO.vbs - Invisible launcher
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get current directory
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Start Python bridge invisibly
objShell.Run "pythonw """ & strPath & "\cloud_bridge.pyw""", 0, False

' Show message
MsgBox "CursorDAW Cloud Bridge Started!" & vbCrLf & vbCrLf & _
       "Now:" & vbCrLf & _
       "1. Open Reaper" & vbCrLf & _
       "2. Load cursordaw_demo.lua" & vbCrLf & _
       "3. Visit: https://feelings36lex36slo-97692729550.europe-west1.run.app" & vbCrLf & vbCrLf & _
       "Bridge is running invisibly in background.", _
       vbInformation, "CursorDAW Cloud Demo"

