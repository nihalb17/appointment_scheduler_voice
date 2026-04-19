param(
  [int]$Port = 8020,
  # Reload can break WebSocket upgrades on some Windows setups; omit unless you need hot reload.
  [switch]$Reload
)

for ($i = 0; $i -lt 12; $i++) {
  $pids = @(
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique |
      Where-Object { $_ -gt 0 }
  )
  if ($pids.Count -eq 0) { break }
  foreach ($procId in $pids) {
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Milliseconds 350
}

Set-Location $PSScriptRoot
$extra = @()
if ($Reload) { $extra += "--reload" }

python -m uvicorn main:app --host 127.0.0.1 --port $Port --ws websockets @extra
