param(
  [string]$BlenderExe = ""
)

# If Blender is not on PATH, pass -BlenderExe "C:\\Path\\to\\blender.exe"
if (-not $BlenderExe) {
  throw "Blender not found on PATH. Re-run with -BlenderExe <full path to blender.exe>"
}

if (-not (Test-Path $BlenderExe)) {
  throw "BlenderExe not found: $BlenderExe"
}

& $BlenderExe --background --python "video_pipeline/blender/build_scene.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Created: video_pipeline/blender/india_network_scene.blend" -ForegroundColor Green
