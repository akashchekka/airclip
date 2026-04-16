"""airclip — Convert videos to ultra-lightweight web-embeddable format.

Takes any video and produces a tiny WebM (VP9) that blends seamlessly
into web pages. Optimized for animation/diagram content where
solid backgrounds and limited motion allow extreme compression.

Usage:
    python -m airclip video.mp4                     # Single file
    python -m airclip video.mp4 --fps 15 --crf 40   # Custom
"""
import argparse
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
        return {"duration": 0, "width": 0, "height": 0, "fps": 30}
    cmd = [
        str(ffprobe), "-v", "quiet",
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
    fps_str = stream.get("r_frame_rate", "30/1")
    num, den = (int(x) for x in fps_str.split("/"))
    return {
        "duration": float(data.get("format", {}).get("duration", 0)),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "fps": num / den if den else 30,
    }


def convert_lightweight(
    input_path: str,
    output_path: str | None = None,
    target_fps: int = 24,
    crf: int = 38,
    max_height: int = 720,
    two_pass: bool = True,
    transparent: bool = False,
) -> dict:
    """Convert a video to ultra-lightweight WebM VP9.

    Args:
        input_path: Source video file.
        output_path: Output path. Default: same name with .webm extension.
        target_fps: Target framerate. 15-24 is ideal for animations.
        crf: Constant Rate Factor. Higher = smaller. 35-45 for animations.
        max_height: Max output height. 720 is good for web.
        two_pass: Use 2-pass encoding for better quality/size ratio.
        transparent: Preserve alpha channel for transparent backgrounds.

    Returns:
        Dict with input_size, output_size, ratio, duration.
    """
    inp = Path(input_path)
    if not inp.exists():
        return {"input": str(inp.name), "output": "", "input_size": 0,
                "output_size": 0, "ratio": 0, "duration": 0,
                "input_kb": 0, "output_kb": 0}
    if output_path is None:
        ext = ".webp" if transparent else ".webm"
        output_path = str(inp.with_suffix(ext))
    out = Path(output_path)

    # Force .webp extension for transparent output
    if transparent and out.suffix != ".webp":
        out = out.with_suffix(".webp")
        output_path = str(out)

    input_size = inp.stat().st_size

    # Validate numeric params
    target_fps = max(1, min(120, target_fps))
    crf = max(0, min(63, crf))
    max_height = max(120, min(4320, max_height))

    # Scale filter: only downscale, keep aspect ratio
    scale_filter = f"scale=-2:'min({max_height},ih)'"
    vf = f"{scale_filter},fps={target_fps}"

    if transparent:
        # Use animated WebP for transparent output (VP9 alpha is unreliable)
        # quality maps roughly: 0=worst, 100=best; invert CRF logic
        webp_quality = max(0, min(100, 100 - (crf - 20) * 2))
        cmd = [
            FFMPEG, "-y", "-i", str(inp),
            "-vf", vf,
            "-c:v", "libwebp_anim",
            "-pix_fmt", "yuva420p",
            "-quality", str(webp_quality),
            "-lossless", "0",
            "-compression_level", "6",
            "-loop", "0",
            "-an",
            str(out),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ERROR encoding {inp.name}: {r.stderr[-200:] if r.stderr else 'unknown error'}")
    elif two_pass:
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
        subprocess.run(pass1, capture_output=True, text=True)

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
        r = subprocess.run(pass2, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ERROR encoding {inp.name}: {r.stderr[-200:] if r.stderr else 'unknown error'}")

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
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ERROR encoding {inp.name}: {r.stderr[-200:] if r.stderr else 'unknown error'}")

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
    parser.add_argument("--transparent", action="store_true", help="Preserve alpha channel for transparent backgrounds")
    parser.add_argument("--outdir", type=str, default=None, help="Output directory")
    args = parser.parse_args()

    target = Path(args.input).resolve()
    if target.is_dir():
        files = sorted(
            p for p in target.iterdir()
            if p.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv", ".webm")
        )
    else:
        files = [target]

    if not files:
        print("No video files found.")
        return

    if not target.exists():
        print(f"Path not found: {target}")
        return

    print(f"\n  Converting {len(files)} video(s) to lightweight {'WebP (transparent)' if args.transparent else 'WebM'}")
    print(f"  Settings: {args.fps}fps, CRF {args.crf}, max {args.height}p, 2-pass={not args.no_2pass}, transparent={args.transparent}")
    print(f"  {'─' * 60}")

    total_in = 0
    total_out = 0

    for f in files:
        out_dir = Path(args.outdir) if args.outdir else f.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_ext = ".webp" if args.transparent else ".webm"
        out_path = out_dir / f"{f.stem}{out_ext}"

        result = convert_lightweight(
            str(f), str(out_path),
            target_fps=args.fps,
            crf=args.crf,
            max_height=args.height,
            two_pass=not args.no_2pass,
            transparent=args.transparent,
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
