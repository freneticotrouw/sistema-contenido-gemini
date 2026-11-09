# Instalador del sistema de contenido (Windows). Uso:
#   irm https://raw.githubusercontent.com/freneticotrouw/sistema-contenido-gemini/main/instalar.ps1 | iex
$ErrorActionPreference = "Stop"
$Repo = "freneticotrouw/sistema-contenido-gemini"
$Destino = Join-Path $HOME "mi-contenido"

function Falta($cmd) { -not (Get-Command $cmd -ErrorAction SilentlyContinue) }
function Instalar($id) { winget install --id $id -e --accept-source-agreements --accept-package-agreements --silent }

Write-Host "1/4 Programas necesarios..."
if (Falta python) { Instalar Python.Python.3.12 }
if (Falta ffmpeg) { Instalar Gyan.FFmpeg }
if (Falta node)   { Instalar OpenJS.NodeJS.LTS }
if (Falta git)    { Instalar Git.Git }
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")

Write-Host "2/4 Herramientas de video y transcripcion (gratis, locales)..."
python -m pip install --upgrade --quiet yt-dlp faster-whisper

Write-Host "3/4 Gemini CLI..."
if (Falta gemini) { npm install -g @google/gemini-cli }

Write-Host "4/4 Carpeta del sistema..."
if (-not (Test-Path $Destino)) {
  $zip = Join-Path $env:TEMP "sistema.zip"
  Invoke-WebRequest "https://github.com/$Repo/archive/refs/heads/main.zip" -OutFile $zip
  Expand-Archive $zip -DestinationPath $env:TEMP -Force
  Move-Item (Join-Path $env:TEMP "sistema-contenido-gemini-main") $Destino
} else { Write-Host "   Ya existe $Destino (no se toca)." }

# Atajo: escribir 'mi-contenido' en PowerShell abre el sistema
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }
if (-not (Select-String -Path $PROFILE -Pattern "function mi-contenido" -Quiet)) {
  Add-Content $PROFILE "`nfunction mi-contenido { Set-Location '$Destino'; gemini }"
}

Write-Host "`nListo. Inicia sesion con tu cuenta de Google (la de tu suscripcion), no con API key."
Write-Host "Luego escribe /empezar. La proxima vez basta con escribir: mi-contenido`n"
Set-Location $Destino
gemini
