workspace_path = inputbox("������Workspace·��")
Set ws = CreateObject("Wscript.Shell")
ws.run "cmd /c python ../fastcgi.py " + workspace_path, vbhide