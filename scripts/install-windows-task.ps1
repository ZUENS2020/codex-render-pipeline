param([Parameter(Mandatory=$true)][string]$Config,[Parameter(Mandatory=$true)][string]$PluginRoot,[string]$Python='pythonw.exe',[string]$TaskName='Codex Render Delivery')
$script = Join-Path $PluginRoot 'scripts\deliver.py'
$action = New-ScheduledTaskAction -Execute $Python -Argument ('"'+$script+'" "'+$Config+'"') -WorkingDirectory (Split-Path $Config)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 100 -RestartInterval (New-TimeSpan -Minutes 1)
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName,State
