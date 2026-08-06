# Rebuild the offline Tailwind CSS bundle.
#
# Uses the Tailwind *standalone* CLI (no Node/npm). If tailwindcss.exe is
# missing, download it once (needs internet just for this step):
#   https://github.com/tailwindlabs/tailwindcss/releases  -> tailwindcss-windows-x64.exe
#   save it next to this script as tailwindcss.exe
#
# Runtime stays fully offline: templates load static/css/styles.css via {% static %}.
#
# Usage:  ./build_css.ps1        (one-off build)
#         ./build_css.ps1 -Watch (rebuild on template changes while developing)

param([switch]$Watch)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path './tailwindcss.exe')) {
    Write-Error "tailwindcss.exe not found. Download the standalone CLI (see header) and place it here."
}

$args = @('-c', 'tailwind.config.js', '-i', 'tailwind/input.css', '-o', 'static/css/styles.css')
if ($Watch) { $args += '--watch' } else { $args += '--minify' }

& ./tailwindcss.exe @args
