# CursorDAW - Upload to Google Drive Helper
# This opens the folder and Google Drive so you can drag-and-drop

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  CursorDAW - Upload to Google Drive" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$zipPath = "$PSScriptRoot\CursorDAW_Demo.zip"

if (Test-Path $zipPath) {
    $size = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
    Write-Host "Found: CursorDAW_Demo.zip ($size MB)" -ForegroundColor Green
} else {
    Write-Host "CursorDAW_Demo.zip not found!" -ForegroundColor Red
    Write-Host "Run the build first." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit
}

Write-Host ""
Write-Host "Opening:" -ForegroundColor Yellow
Write-Host "  1. File Explorer (with the zip selected)"
Write-Host "  2. Google Drive in your browser"
Write-Host ""

# Open File Explorer with the zip selected
Start-Process explorer.exe -ArgumentList "/select,`"$zipPath`""

# Wait a moment then open Google Drive
Start-Sleep -Seconds 1
Start-Process "https://drive.google.com/drive/my-drive"

Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. Drag CursorDAW_Demo.zip from Explorer to Google Drive"
Write-Host "  2. Wait for upload to complete"
Write-Host "  3. Right-click the file > Share > 'Anyone with link'"
Write-Host "  4. Copy the link and share it!"
Write-Host ""
Write-Host "Done! Close this window when finished." -ForegroundColor Green
Read-Host "Press Enter to exit"

