# Create Startup Shortcut for AI-Native SDLC Engine

$StartupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$ShortcutPath = "$StartupFolder\AI-Native SDLC Engine Server.lnk"
$TargetPath = "$PSScriptRoot\start-ai-native-sdlc-engine.bat"
$WorkingDir = Split-Path $PSScriptRoot

Write-Host ""
Write-Host "Creating startup shortcut..."
Write-Host "Target: $TargetPath"
Write-Host "Location: $ShortcutPath"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.Description = "Start AI-Native SDLC Engine Server on Login"
$Shortcut.Save()

Write-Host ""
Write-Host "[OK] Shortcut created successfully!"
Write-Host "[OK] AI-Native SDLC Engine will start on next login"
Write-Host ""
