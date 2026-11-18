<#
.SYNOPSIS
    Standalone emergency restoration script for NetGuard AI (Item D4).
    Removes all NetGuard Windows QoS policies and Firewall rules cleanly.

.DESCRIPTION
    Can be run independently by the user or an automated recovery task even if
    the NetGuard desktop application was abruptly terminated or crashed.
#>

Write-Host "NetGuard Emergency Rule Cleaner & QoS Reset..." -ForegroundColor Cyan

# 1. Remove NetGuard QoS Policies
try {
    $qosPolicies = Get-NetQosPolicy -Name "NetGuard_*" -ErrorAction SilentlyContinue
    if ($qosPolicies) {
        Write-Host "Found $($qosPolicies.Count) NetGuard QoS policies. Removing..." -ForegroundColor Yellow
        Remove-NetQosPolicy -Name "NetGuard_*" -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Cleaned all NetGuard QoS policies successfully." -ForegroundColor Green
    } else {
        Write-Host "No active NetGuard QoS policies found." -ForegroundColor DarkGray
    }
} catch {
    Write-Warning "Could not query or remove QoS policies: $_"
}

# 2. Remove NetGuard Firewall Rules
try {
    $fwRules = Get-NetFirewallRule -Name "NetGuard_*" -ErrorAction SilentlyContinue
    if ($fwRules) {
        Write-Host "Found $($fwRules.Count) NetGuard Firewall rules. Removing..." -ForegroundColor Yellow
        Remove-NetFirewallRule -Name "NetGuard_*" -ErrorAction SilentlyContinue
        Write-Host "Cleaned all NetGuard Firewall rules successfully." -ForegroundColor Green
    } else {
        Write-Host "No active NetGuard Firewall rules found." -ForegroundColor DarkGray
    }
} catch {
    Write-Warning "Could not query or remove Firewall rules: $_"
}

Write-Host "System network stack restored to default state." -ForegroundColor Cyan
