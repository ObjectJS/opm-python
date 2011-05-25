workspace_path = inputbox("«Î ‰»ÎWorkspace¬∑æ∂")
Set ws = CreateObject("Wscript.Shell")
ws.run "cmd /c python ../fastcgi.py " + workspace_path, vbhide