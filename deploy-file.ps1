<#
.SYNOPSIS
  Safely apply a file Claude gave you: copies it from Downloads into your
  repo, PROVES the file actually changed (git diff), then commits & pushes.
  This exists because copying a downloaded file into place is the one step
  that kept silently failing (git saw "nothing to commit" because the file
  was never actually replaced).

.USAGE
  Run this from inside your repo folder (e.g. standingup-backend-only):

  .\deploy-file.ps1 -DownloadName "auth.py" -DestPath "app\routes\auth.py" -Message "Fix password reset email"

  -DownloadName : exact filename as it landed in your Downloads folder
  -DestPath     : where it goes, RELATIVE to the repo root you're standing in
  -Message      : git commit message
#>

param(
    [Parameter(Mandatory=$true)][string]$DownloadName,
    [Parameter(Mandatory=$true)][string]$DestPath,
    [Parameter(Mandatory=$true)][string]$Message
)

$ErrorActionPreference = "Stop"

# 1. Confirm we're inside a git repo
if (-not (Test-Path ".git")) {
    Write-Host "ERROR: No .git folder here. cd into your repo first." -ForegroundColor Red
    exit 1
}

# 2. Find the downloaded file
$downloadPath = Join-Path "$env:USERPROFILE\Downloads" $DownloadName
if (-not (Test-Path $downloadPath)) {
    Write-Host "ERROR: Could not find $downloadPath" -ForegroundColor Red
    Write-Host "Files actually in Downloads matching similar names:" -ForegroundColor Yellow
    Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "*$($DownloadName.Split('.')[0])*" | Format-Table Name, LastWriteTime
    exit 1
}

# 3. Snapshot the destination file's content BEFORE overwrite (may not exist yet)
$before = if (Test-Path $DestPath) { Get-Content $DestPath -Raw } else { "" }

# 4. Copy into place
$destDir = Split-Path $DestPath -Parent
if ($destDir) {
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
}
Copy-Item $downloadPath -Destination $DestPath -Force
Write-Host "Copied $DownloadName -> $DestPath" -ForegroundColor Green

# 5. PROVE it actually changed
$after = Get-Content $DestPath -Raw
if ($before -eq $after) {
    Write-Host "WARNING: File content is IDENTICAL to what was already there." -ForegroundColor Yellow
    Write-Host "Either this file was already up to date, or something's wrong. Aborting commit." -ForegroundColor Yellow
    exit 1
}
Write-Host "Confirmed: file content changed on disk." -ForegroundColor Green

# 6. Show git status/diff so you can SEE the real change before it's committed
git add $DestPath
Write-Host "`n--- git diff (staged) ---" -ForegroundColor Cyan
git diff --cached --stat
git diff --cached | Select-Object -First 40

# 7. Commit and push
git commit -m $Message
git push

Write-Host "`nDone. Pushed: $Message" -ForegroundColor Green
