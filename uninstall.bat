@echo off
chcp 65001 >nul
echo =======================================================
echo        Antigravity Token - 一键卸载与还原
echo =======================================================
echo.

set "ANTIGRAVITY_EXE=%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe"
if not exist "%ANTIGRAVITY_EXE%" (
    if exist "C:\Program Files\Antigravity\Antigravity.exe" (
        set "ANTIGRAVITY_EXE=C:\Program Files\Antigravity\Antigravity.exe"
    )
)

echo [1/2] 停止正在运行的托盘进程...
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq AntigravityToken*" >nul 2>&1
echo      -> 托盘进程已停止。

echo [2/2] 还原开始菜单与桌面快捷方式为原版...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$sh = New-Object -ComObject WScript.Shell; " ^
    "$workDir = [System.IO.Path]::GetDirectoryName('%ANTIGRAVITY_EXE%'); " ^
    "$startMenuLnk = [System.Environment]::GetFolderPath('Programs') + '\Antigravity.lnk'; " ^
    "if (Test-Path $startMenuLnk) { " ^
    "    $lnk = $sh.CreateShortcut($startMenuLnk); " ^
    "    $lnk.TargetPath = '%ANTIGRAVITY_EXE%'; " ^
    "    $lnk.Arguments = ''; " ^
    "    $lnk.WorkingDirectory = $workDir; " ^
    "    $lnk.IconLocation = '%ANTIGRAVITY_EXE%,0'; " ^
    "    $lnk.Save(); " ^
    "    Write-Host '     -> 开始菜单快捷方式已成功恢复为原版！'; " ^
    "} " ^
    "$desktopLnk = [System.Environment]::GetFolderPath('Desktop') + '\Antigravity.lnk'; " ^
    "if (Test-Path $desktopLnk) { " ^
    "    $lnk2 = $sh.CreateShortcut($desktopLnk); " ^
    "    $lnk2.TargetPath = '%ANTIGRAVITY_EXE%'; " ^
    "    $lnk2.Arguments = ''; " ^
    "    $lnk2.WorkingDirectory = $workDir; " ^
    "    $lnk2.IconLocation = '%ANTIGRAVITY_EXE%,0'; " ^
    "    $lnk2.Save(); " ^
    "    Write-Host '     -> 桌面快捷方式已成功恢复为原版！'; " ^
    "}"

echo.
echo =======================================================
echo   还原成功！快捷方式已恢复为官方原生直接启动。
echo =======================================================
echo.
pause
