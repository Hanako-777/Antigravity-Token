@echo off
chcp 65001 >nul
echo =======================================================
echo        Antigravity Token - 一键安装与联动配置
echo =======================================================
echo.

:: 1. 获取当前脚本所在目录
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo [1/4] 检查并安装 Python 依赖库 (pystray, pillow)...
python -m pip install -r "%PROJECT_DIR%\requirements.txt" --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [错误] Python 依赖安装失败，请确保电脑已安装 Python 并已添加至环境变量。
    pause
    exit /b 1
)
echo      -> 依赖安装完成。

:: 2. 探测 pythonw.exe 路径
echo [2/4] 探测系统环境与可执行程序...
set "PYTHONW_PATH="
for /f "delims=" %%I in ('where pythonw 2^>nul') do (
    if not defined PYTHONW_PATH set "PYTHONW_PATH=%%I"
)

if not defined PYTHONW_PATH (
    if exist "%LOCALAPPDATA%\Programs\Python\Python*\pythonw.exe" (
        for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
            if exist "%%D\pythonw.exe" set "PYTHONW_PATH=%%D\pythonw.exe"
        )
    )
)

if not defined PYTHONW_PATH (
    echo [错误] 未能找到 pythonw.exe，请确保系统已安装 Python 3.8+。
    pause
    exit /b 1
)
echo      -> 找到 Python 运行时: %PYTHONW_PATH%

:: 3. 探测 Antigravity.exe 路径
set "ANTIGRAVITY_EXE=%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe"
if not exist "%ANTIGRAVITY_EXE%" (
    if exist "C:\Program Files\Antigravity\Antigravity.exe" (
        set "ANTIGRAVITY_EXE=C:\Program Files\Antigravity\Antigravity.exe"
    ) else (
        echo [警告] 未能自动定位 Antigravity.exe 默认路径，将采用标准路径。
    )
)
echo      -> 找到 Antigravity 路径: %ANTIGRAVITY_EXE%

:: 4. 动态生成个性化静默启动调度脚本 launch_antigravity.vbs
echo [3/4] 生成静默联动启动器 (launch_antigravity.vbs)...
set "VBS_FILE=%PROJECT_DIR%\launch_antigravity.vbs"

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set objWMIService = GetObject^("winmgmts:\\.\root\cimv2"^)
echo Set colProcesses = objWMIService.ExecQuery^("Select * from Win32_Process Where Name = 'pythonw.exe' and CommandLine Like '%%antigravity_tray.py%%'"^)
echo If colProcesses.Count = 0 Then
echo     WshShell.Run """%PYTHONW_PATH%"" ""%PROJECT_DIR%\antigravity_tray.py""", 0, False
echo End If
echo WshShell.Run """%ANTIGRAVITY_EXE%""", 1, False
) > "%VBS_FILE%"
echo      -> 启动调度脚本配置完成。

:: 5. 绑定开始菜单与桌面快捷方式
echo [4/4] 绑定 Windows 开始菜单与桌面快捷方式...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$sh = New-Object -ComObject WScript.Shell; " ^
    "$vbsPath = '%VBS_FILE%'.Replace('\', '\\'); " ^
    "$iconPath = '%ANTIGRAVITY_EXE%,0'.Replace('\', '\\'); " ^
    "$workDir = [System.IO.Path]::GetDirectoryName('%ANTIGRAVITY_EXE%'); " ^
    "$startMenuLnk = [System.Environment]::GetFolderPath('Programs') + '\Antigravity.lnk'; " ^
    "if (Test-Path $startMenuLnk) { " ^
    "    $lnk = $sh.CreateShortcut($startMenuLnk); " ^
    "    $lnk.TargetPath = 'wscript.exe'; " ^
    "    $lnk.Arguments = '\"' + '%VBS_FILE%' + '\"'; " ^
    "    $lnk.WorkingDirectory = $workDir; " ^
    "    $lnk.IconLocation = '%ANTIGRAVITY_EXE%,0'; " ^
    "    $lnk.Description = 'Google Antigravity'; " ^
    "    $lnk.Save(); " ^
    "    Write-Host '     -> 开始菜单 Antigravity 快捷方式已成功绑定！'; " ^
    "} else { Write-Host '     -> 未检测到开始菜单图标，跳过。'; } " ^
    "$desktopLnk = [System.Environment]::GetFolderPath('Desktop') + '\Antigravity.lnk'; " ^
    "if (Test-Path $desktopLnk) { " ^
    "    $lnk2 = $sh.CreateShortcut($desktopLnk); " ^
    "    $lnk2.TargetPath = 'wscript.exe'; " ^
    "    $lnk2.Arguments = '\"' + '%VBS_FILE%' + '\"'; " ^
    "    $lnk2.WorkingDirectory = $workDir; " ^
    "    $lnk2.IconLocation = '%ANTIGRAVITY_EXE%,0'; " ^
    "    $lnk2.Description = 'Google Antigravity'; " ^
    "    $lnk2.Save(); " ^
    "    Write-Host '     -> 桌面 Antigravity 快捷方式已成功绑定！'; " ^
    "}"

echo.
echo =======================================================
echo   配置成功！从现在起，打开 Antigravity 时
echo   右下角蓝粉星芒 Token 看板将自动随同启动！
echo =======================================================
echo.
pause
