# India 3D Network Hero Video (Generation Pipeline)
This folder contains scripts to help you generate a cinematic 3D India logistics network video (MP4) for the website home page.
## What you already have in the website
The home page video section is already wired to:
- `main/static/main/videos/Deep_Record.mp4`
After you render the final hero video, replace that file (keep the same name) to show it on the home page.
## Step 1: Install Python deps (for geocoding)
```powershell
pip install -r video_pipeline/requirements.txt
```
## Step 2: Generate city latitude/longitude (pins)
Before running, update the User-Agent in `video_pipeline/geocode_locations.py` with your email.
```powershell
python video_pipeline/geocode_locations.py
```
Output:
- `video_pipeline/locations_geocoded.json`
If some locations fail, add coordinates to:
- `video_pipeline/geocode_manual_overrides.json`
Then rerun.
## Step 3: India states SVG (already added)
This repo now contains:
- `video_pipeline/assets/india_states.svg`
It includes `id` + `name` per state (example: `INMH` for Maharashtra), which helps for state-wise highlighting.
## Step 4: Build the Blender scene from pins + SVG (Blender 4.1)
Blender is installed but may not be on PATH. Use the helper script and pass your full `blender.exe` path.
Example path is often like:
- `C:\\Program Files\\Blender Foundation\\Blender 4.1\\blender.exe`
Run:
```powershell
powershell -ExecutionPolicy Bypass -File video_pipeline/run_blender_build.ps1 -BlenderExe "C:\\FULL\\PATH\\TO\\blender.exe"
```
This generates:
- `video_pipeline/blender/india_network_scene.blend`
Open that `.blend` in Blender UI and do the cinematic tuning:
- state outline glow timing (Maharashtra → CG → Delhi → Punjab → UP → Haryana → Gujarat)
- connection line curves (thin animated lines)
- slow camera pan/zoom between regions
- floating 3D labels
- lighting for soft global illumination / elegant contrast
## Render settings (recommended)
- Resolution: 3840x2160 (4K)
- FPS: 30
- Duration: 12–18 seconds (loop-friendly)
- Output: MP4 (H.264), no audio
## Step 5: Render MP4 and put it into the website
After you are happy with the scene in Blender UI, render to the website path:
```powershell
powershell -ExecutionPolicy Bypass -File video_pipeline/run_blender_render.ps1 -BlenderExe "C:\\FULL\\PATH\\TO\\blender.exe"
```
Output:
- `main/static/main/videos/Deep_Record.mp4`
Then refresh the home page.
