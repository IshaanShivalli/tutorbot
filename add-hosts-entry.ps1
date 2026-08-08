# PowerShell script to add tutorbot.all.edu to Windows hosts file
# Run as Administrator

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "This script must be run as Administrator. Restarting with elevated privileges..." -ForegroundColor Red
    Start-Process powershell -ArgumentList "-File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$entry = "127.0.0.1`ttutorbot.all.edu"
$newLine = "`n127.0.0.1`ttutorbot.all.edu"

# Read the hosts file
$hostsContent = Get-Content $hostsPath -Raw

# Check if entry already exists
if ($hostsContent -match "tutorbot\.all\.edu") {
    Write-Host "Entry 'tutorbot.all.edu' already exists in hosts file." -ForegroundColor Green
} else {
    # Add the entry to the end of the file (before the last newline if it exists)
    $hostsContent = $hostsContent.TrimEnd() + $newLine
    
    # Write back to hosts file
    Set-Content -Path $hostsPath -Value $hostsContent -Encoding ASCII
    
    Write-Host "Successfully added '127.0.0.1  tutorbot.all.edu' to hosts file!" -ForegroundColor Green
}

Write-Host "`nYou can now access the server at: http://tutorbot.all.edu:5000/" -ForegroundColor Cyan
Write-Host "Make sure your Flask server is running on port 5000!" -ForegroundColor Cyan

Read-Host "Press Enter to exit"
