$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$source = Join-Path (Split-Path $PSScriptRoot) 'Windows-MCP'
if (!(Test-Path "$source/pyproject.toml")) { throw 'Local Windows-MCP source is missing next to this project.' }
py -3.14 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Install Windows Python 3.14 with Tcl/Tk.' }
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $python -m pip install --force-reinstall --no-deps "$source"
if ($LASTEXITCODE -ne 0) { throw 'Local Windows-MCP installation failed.' }
& $python engine.py serve --help
if ($LASTEXITCODE -ne 0) { throw 'Local MCP engine entry point failed.' }
$tcl = 'import tkinter; print(tkinter.Tcl().eval("info library"))' | & $python -
if ($LASTEXITCODE -ne 0) { throw 'Tcl installation is broken.' }
$tcl = "$tcl".Trim()
if ([string]::IsNullOrWhiteSpace($tcl)) { throw 'Tcl library detection returned an empty path.' }
$embeddedTcl = $tcl.StartsWith('//zipfs:/')
Write-Host "Tcl resources: $tcl"
& $python -m PyInstaller --noconfirm --clean QZdeskConnector.spec
if ($LASTEXITCODE -ne 0) { throw 'GUI packaging failed.' }
& $python -m PyInstaller --noconfirm --clean --onedir --console --name QZdeskMcpEngine --collect-all windows_mcp --copy-metadata windows-mcp --exclude-module tkinter --distpath engine-dist engine.py
if ($LASTEXITCODE -ne 0) { throw 'Engine packaging failed.' }
New-Item -ItemType Directory -Force dist/QZdeskConnector/engine | Out-Null
Copy-Item engine-dist/QZdeskMcpEngine/* dist/QZdeskConnector/engine/ -Recurse -Force
if (!$embeddedTcl -and (!(Test-Path dist/QZdeskConnector/_internal/_tcl_data/init.tcl) -or !(Test-Path dist/QZdeskConnector/_internal/_tk_data/tk.tcl))) { throw 'Packaged Tcl/Tk validation failed.' }
Compress-Archive -Path dist/QZdeskConnector -DestinationPath QZdeskConnector-Windows.zip -Force
Write-Host 'Output: dist/QZdeskConnector/QZdeskConnector.exe and QZdeskConnector-Windows.zip'
