' poll_http.vbs — silent HTTP poll, no windows
On Error Resume Next
Dim http, fso, f, resp
Set http = CreateObject("MSXML2.XMLHTTP")
http.Open "GET", "https://feelings36lex36slo-97692729550.europe-west1.run.app/api/reaper/poll?session_id=demo", False
http.Send
If http.Status = 200 Then
  resp = http.responseText
  If Len(resp) > 0 And resp <> "null" Then
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set f = fso.CreateTextFile("C:\\Users\\moosb\\AIAGENT DAW\\reaper_commands.txt", True)
    f.Write resp
    f.Close
  End If
End If


