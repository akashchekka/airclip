"""nanoclip — Convert videos to ultra-lightweight web-embeddable format.

Takes any video and produces a tiny WebM (VP9) that blends seamlessly
into web pages. Optimized for animation/diagram content where
solid backgrounds and limited motion allow extreme compression.

Usage:
    python -m nanoclip video.mp4                     # Single file
    python -m nanoclip video.mp4 --fps 15 --crf 40   # Custom
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# imageio-ffmpeg bundles ffmpeg so we don't need a system install
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"


def get_video_info(path: str) -> dict:
    """Get duration and resolution using ffprobe."""
    ffprobe = Path(FFMPEG).parent / Path(FFMPEG).name.replace("ffmpeg", "ffprobe")
    if not ffprobe.exists():
        # Fall back: try without info
        return {"duration": 0, "width": 0, "height": 0, "fps": 30}
    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ]
    import json
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    data = json.loads(r.stdout)
    stream = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), {})
    return {
        "duration": float(data.get("format", {}).get("duration", 0)),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "fps": eval(stream.get("r_frame_rate", "30/1")),
    }


def convert_lightweight(
    input_path: str,
    output_path: str | None = None,
    target_fps: int = 24,
    crf: int = 38,
    max_height: int = 720,
    two_pass: bool = True,
) -> dict:
    """Convert a video to ultra-lightweight WebM VP9.

    Args:
        input_path: Source video file.
        output_path: Output path. Default: same name with .webm extension.
        target_fps: Target framerate. 15-24 is ideal for animations.
        crf: Constant Rate Factor. Higher = smaller. 35-45 for animations.
        max_height: Max output height. 720 is good for web.
        two_pass: Use 2-pass encoding for better quality/size ratio.

    Returns:
        Dict with input_size, output_size, ratio, duration.
    """
    inp = Path(input_path)
    if output_path is None:
        output_path = str(inp.with_suffix(".webm"))
    out = Path(output_path)

    input_size = inp.stat().st_size

    # Scale filter: only downscale, keep aspect ratio
    scale_filter = f"scale=-2:'min({max_height},ih)'"
    vf = f"{scale_filter},fps={target_fps}"

    if two_pass:
        # Pass 1: analyze
        pass1 = [
            FFMPEG, "-y", "-i", str(inp),
            "-vf", vf,
            "-c:v", "libvpx-vp9",
            "-b:v", "0", "-crf", str(crf),
            "-pass", "1",
            "-an",
            "-f", "null",
            "NUL" if sys.platform == "win32" else "/dev/null",
        ]
        subprocess.run(pass1, capture_output=True)

        # Pass 2: encode
        pass2 = [
            FFMPEG, "-y", "-i", str(inp),
            "-vf", vf,
            "-c:v", "libvpx-vp9",
            "-b:v", "0", "-crf", str(crf),
            "-pass", "2",
            "-an",  # no audio for animations
            "-auto-alt-ref", "1",
            "-lag-in-frames", "25",
            "-row-mt", "1",
            str(out),
        ]
        subprocess.run(pass2, capture_output=True)

        # Cleanup pass log files
        for f in Path(".").glob("ffmpeg2pass-0*"):
            f.unlink(missing_ok=True)
    else:
        cmd = [
            FFMPEG, "-y", "-i", str(inp),
            "-vf", vf,
            "-c:v", "libvpx-vp9",
            "-b:v", "0", "-crf", str(crf),
            "-an",
            "-row-mt", "1",
            str(out),
        ]
        subprocess.run(cmd, capture_output=True)

    output_size = out.stat().st_size if out.exists() else 0
    info = get_video_info(str(inp))

    return {
        "input": str(inp.name),
        "output": str(out.name),
        "input_size": input_size,
        "output_size": output_size,
        "ratio": input_size / output_size if output_size else 0,
        "duration": info.get("duration", 0),
        "input_kb": input_size / 1024,
        "output_kb": output_size / 1024,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert videos to lightweight web-embeddable format")
    parser.add_argument("input", help="Video file or directory of videos")
    parser.add_argument("--fps", type=int, default=24, help="Target FPS (default: 24)")
    parser.add_argument("--crf", type=int, default=38, help="Quality (higher=smaller, default: 38)")
    parser.add_argument("--height", type=int, default=720, help="Max height in px (default: 720)")
    parser.add_argument("--no-2pass", action="store_true", help="Skip 2-pass encoding (faster)")
    parser.add_argument("--outdir", type=str, default=None, help="Output directory")
    args = parser.parse_args()

    target = Path(args.input)
    if target.is_dir():
        files = sorted(target.glob("*.mp4"))
    else:
        files = [target]

    if not files:
        print("No MP4 files found.")
        return

    print(f"\n  Converting {len(files)} video(s) to lightweight WebM")
    print(f"  Settings: {args.fps}fps, CRF {args.crf}, max {args.height}p, 2-pass={not args.no_2pass}")
    print(f"  {'─' * 60}")

    total_in = 0
    total_out = 0

    for f in files:
        out_dir = Path(args.outdir) if args.outdir else f.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{f.stem}.webm"

        result = convert_lightweight(
            str(f), str(out_path),
            target_fps=args.fps,
            crf=args.crf,
            max_height=args.height,
            two_pass=not args.no_2pass,
        )

        total_in += result["input_size"]
        total_out += result["output_size"]

        print(
            f"  {result['input']:40s} "
            f"{result['input_kb']:7.0f} KB → {result['output_kb']:6.0f} KB "
            f"({result['ratio']:5.1f}x smaller)"
        )

    print(f"  {'─' * 60}")
    print(
        f"  Total: {total_in/1024:,.0f} KB → {total_out/1024:,.0f} KB "
        f"({total_in/total_out:.1f}x compression)"
    )
    print()


if __name__ == "__main__":
    main()
