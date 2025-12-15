param(
  [string]$BlenderExe = "",
  [string]$Out = "main/static/main/videos/Deep_Record.mp4"
)

if (-not $BlenderExe) {
  throw "Blender not found on PATH. Re-run with -BlenderExe <full path to blender.exe>"
}

if (-not (Test-Path $BlenderExe)) {
  throw "BlenderExe not found: $BlenderExe"
}

$blend = "video_pipeline/blender/india_network_scene.blend"
if (-not (Test-Path $blend)) {
  throw "Missing $blend. Run video_pipeline/run_blender_build.ps1 first (and optionally edit in Blender UI)."
}

& $BlenderExe --background $blend --python "video_pipeline/blender/render_mp4.py" -- --out $Out
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Rendered: $Out" -ForegroundColor Green
