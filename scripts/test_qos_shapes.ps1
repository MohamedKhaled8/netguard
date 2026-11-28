# NetGuard AI - Windows Native QoS Self-Test Script
# Tests all NetGuard policy shapes in ActiveStore with exact property readback and guaranteed cleanup.
# Requires Administrator privileges.

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " NetGuard AI - Windows QoS Policy Shapes Self-Test" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Elevation check
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "This self-test requires an ELEVATED (Administrator) PowerShell session. Please re-run as Administrator."
    exit 1
}

$testGuid = [Guid]::NewGuid().ToString("N").Substring(0, 12)
$createdPolicies = @()
$testPassed = $true

function Cleanup-TestPolicies {
    param([string[]]$Policies)
    Write-Host "`n[Cleanup] Removing temporary self-test policies..." -ForegroundColor Yellow
    $allCleaned = $true
    foreach ($p in $Policies) {
        try {
            Remove-NetQosPolicy -Name $p -PolicyStore ActiveStore -Confirm:$false -ErrorAction Stop
            Write-Host "  [CLEANED] $p" -ForegroundColor Green
        } catch {
            Write-Warning "  [CLEANUP_WARN] Failed to remove $p : $_"
            $allCleaned = $false
        }
    }
    
    # Final verification
    $remaining = Get-NetQosPolicy -PolicyStore ActiveStore -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "netguard_test_*" }
    if ($remaining -and $remaining.Count -gt 0) {
        Write-Host "CLEANUP=FAIL (Remaining policies found: $($remaining.Name -join ', '))" -ForegroundColor Red
    } else {
        Write-Host "CLEANUP=PASS" -ForegroundColor Green
    }
}

try {
    # -------------------------------------------------------------
    # Shape 1: Meeting Media UDP Outbound Priority (AF41 / DSCP 34)
    # -------------------------------------------------------------
    $p1 = "netguard_test_media_$testGuid"
    Write-Host "`n[Test 1/4] Creating Shape 1 (Media Priority: Zoom.exe UDP 8801-8810 DSCP 34 Precedence 200)..." -ForegroundColor White
    New-NetQosPolicy -Name $p1 -AppPathNameMatchCondition "Zoom.exe" -IPProtocolMatchCondition UDP -IPDstPortStartMatchCondition 8801 -IPDstPortEndMatchCondition 8810 -DSCPAction 34 -Precedence 200 -PolicyStore ActiveStore | Out-Null
    $createdPolicies += $p1

    $r1 = Get-NetQosPolicy -Name $p1 -PolicyStore ActiveStore
    if ($r1.DSCPAction -eq 34 -and $r1.Precedence -eq 200 -and $r1.AppPathNameMatchCondition -eq "Zoom.exe" -and $r1.IPDstPortStartMatchCondition -eq 8801) {
        Write-Host "  [PASS] Shape 1 verified in ActiveStore with matching properties." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Shape 1 properties mismatch: DSCP=$($r1.DSCPAction), Precedence=$($r1.Precedence)" -ForegroundColor Red
        $testPassed = $false
    }

    # -------------------------------------------------------------
    # Shape 2: Background Default Demotion (CS1 / DSCP 8)
    # -------------------------------------------------------------
    $p2 = "netguard_test_default_$testGuid"
    Write-Host "`n[Test 2/4] Creating Shape 2 (Default Demote: DSCP 8 Precedence 50)..." -ForegroundColor White
    New-NetQosPolicy -Name $p2 -DSCPAction 8 -Precedence 50 -PolicyStore ActiveStore | Out-Null
    $createdPolicies += $p2

    $r2 = Get-NetQosPolicy -Name $p2 -PolicyStore ActiveStore
    if ($r2.DSCPAction -eq 8 -and $r2.Precedence -eq 50) {
        Write-Host "  [PASS] Shape 2 verified in ActiveStore with matching properties." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Shape 2 properties mismatch: DSCP=$($r2.DSCPAction), Precedence=$($r2.Precedence)" -ForegroundColor Red
        $testPassed = $false
    }

    # -------------------------------------------------------------
    # Shape 3: Bulk Upload Throttling (Combined DSCP 8 + Rate Limit)
    # -------------------------------------------------------------
    $p3 = "netguard_test_throttle_$testGuid"
    Write-Host "`n[Test 3/4] Creating Shape 3 (Bulk Throttle: TCP DSCP 8 + 5 Mbps Precedence 100)..." -ForegroundColor White
    New-NetQosPolicy -Name $p3 -IPProtocolMatchCondition TCP -DSCPAction 8 -ThrottleRateActionBitsPerSecond 5000000 -Precedence 100 -PolicyStore ActiveStore | Out-Null
    $createdPolicies += $p3

    $r3 = Get-NetQosPolicy -Name $p3 -PolicyStore ActiveStore
    if ($r3.DSCPAction -eq 8 -and $r3.ThrottleRateActionBitsPerSecond -eq 5000000 -and $r3.Precedence -eq 100) {
        Write-Host "  [PASS] Shape 3 verified in ActiveStore with matching properties." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Shape 3 properties mismatch: DSCP=$($r3.DSCPAction), ThrottleRate=$($r3.ThrottleRateActionBitsPerSecond)" -ForegroundColor Red
        $testPassed = $false
    }

    # -------------------------------------------------------------
    # Shape 4: DNS Exemption (UDP 53 Exemption DSCP 0 Precedence 160)
    # -------------------------------------------------------------
    $p4 = "netguard_test_dns_$testGuid"
    Write-Host "`n[Test 4/4] Creating Shape 4 (DNS Exemption: UDP 53 DSCP 0 Precedence 160)..." -ForegroundColor White
    New-NetQosPolicy -Name $p4 -IPProtocolMatchCondition UDP -IPDstPortStartMatchCondition 53 -IPDstPortEndMatchCondition 53 -DSCPAction 0 -Precedence 160 -PolicyStore ActiveStore | Out-Null
    $createdPolicies += $p4

    $r4 = Get-NetQosPolicy -Name $p4 -PolicyStore ActiveStore
    if ($r4.DSCPAction -eq 0 -and $r4.Precedence -eq 160 -and $r4.IPDstPortStartMatchCondition -eq 53) {
        Write-Host "  [PASS] Shape 4 verified in ActiveStore with matching properties." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Shape 4 properties mismatch: DSCP=$($r4.DSCPAction), Precedence=$($r4.Precedence)" -ForegroundColor Red
        $testPassed = $false
    }

} catch {
    Write-Host "`n[ERROR] An exception occurred during self-test: $_" -ForegroundColor Red
    $testPassed = $false
} finally {
    Cleanup-TestPolicies -Policies $createdPolicies
}

Write-Host "==========================================================" -ForegroundColor Cyan
if ($testPassed) {
    Write-Host " RESULT: ALL 4 QOS POLICY SHAPES PASSED ACTIVE STORE VERIFICATION!" -ForegroundColor Green
} else {
    Write-Host " RESULT: SOME POLICY SHAPES FAILED VERIFICATION." -ForegroundColor Red
}
Write-Host "==========================================================" -ForegroundColor Cyan
