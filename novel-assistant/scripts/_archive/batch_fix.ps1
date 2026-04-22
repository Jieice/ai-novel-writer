# batch auto_fix - PowerShell版
$project = "d:/AI/AI小说创作系统/山村小神医"
$chapters = @(1, 2, 3, 5, 13, 26)

$results = @()

foreach ($ch in $chapters) {
    Write-Host ">>> Processing Chapter $ch..."
    $rc = 0
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "python"
        $psi.Arguments = "`"d:/AI/AI小说创作系统/novel-assistant/scripts/auto_fix_chapter.py`" --project `"$project`" --chapter $ch --strict"
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

        $proc = [System.Diagnostics.Process]::Start($psi)
        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()
        $rc = $proc.ExitCode
    } catch {
        Write-Host "[ERROR] $_"
        $rc = 999
    }

    $results += [PSCustomObject]@{
        Chapter = "Ch$ch"
        ExitCode = $rc
    }
    Write-Host "    rc=$rc"
}

Write-Host ""
Write-Host "=== Summary ==="
$results | Format-Table
