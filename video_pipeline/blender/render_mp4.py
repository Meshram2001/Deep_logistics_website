"""Headless render to MP4.

Usage (PowerShell):
  & $BlenderExe --background video_pipeline/blender/india_network_scene.blend --python video_pipeline/blender/render_mp4.py -- \
    --out main/static/main/videos/Deep_Record.mp4

Notes:
- This uses Blender's FFmpeg output (H.264) and renders the full frame range.
- For best results, open the .blend in Blender UI first and tune:
  camera, materials, bloom/glow, connection lines, labels, etc.
"""

import argparse
from pathlib import Path

import bpy


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--out", required=True)
    args, _unknown = parser.parse_known_args()
    return args


def main():
    args = parse_args()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene

    # Output settings
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.gopsize = 12
    scene.render.ffmpeg.audio_codec = "NONE"

    scene.render.filepath = str(out_path)

    bpy.ops.render.render(animation=True)
    print(f"Rendered MP4 to {out_path}")


if __name__ == "__main__":
    main()
