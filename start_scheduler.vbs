' 洛川调度器 - 静默启动脚本（无命令行窗口）
' 将此文件的快捷方式放入启动文件夹即可开机自启

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
schedulerScript = scriptDir & "\scheduler.py"
logDir = scriptDir & "\data"

' 如果日志目录不存在则创建
If Not FSO.FolderExists(logDir) Then
    FSO.CreateFolder(logDir)
End If

' 查找 Python 解释器
pythonExe = "pythonw.exe"

' 优先使用 pythonw.exe（无窗口），否则使用 python.exe
If Not WshShell.Run("where pythonw.exe 2>nul", 0, True) = 0 Then
    pythonExe = "python.exe"
End If

' 静默启动 Python 调度器
WshShell.Run """" & pythonExe & """ """ & schedulerScript & """", 0, False
