# airclip

Convert any video to an ultra-lightweight web-embeddable format.

**30 seconds of video → ~50-200 KB** without visible quality loss.

Two output modes:

| Mode | Format | Use case | Embed with |
|------|--------|----------|------------|
| Standard | WebM (VP9) | Solid-background animations | `<video>` |
| Transparent | Animated WebP | Alpha-channel animations | `<img>` |

## Why

Embedding videos on the web usually means large files, slow loads, and visible player chrome. `airclip` solves this for animation and diagram content:

| | Standard mode | Transparent mode |
|--|---------------|------------------|
| Input | MP4, MOV, AVI, MKV, WebM | MOV with alpha (e.g. Manim `-t`) |
| Output | WebM (VP9) | Animated WebP |
| 30s video | ~50-200 KB | ~150-500 KB |
| Background | Solid color (blends in) | Fully transparent |

The output looks native to the page — no borders, no player UI, just content.

## How it works

**Standard mode** (WebM VP9):
1. **VP9 encoding** — modern codec, much better compression than H.264
2. **High CRF** — animation content compresses extremely well at CRF 35-45
3. **Reduced framerate** — 24fps is visually identical to 60fps for diagrams
4. **Downscale to 720p** — on web, nobody notices the difference from 1080p
5. **Two-pass encoding** — analyzes content first, allocates bits where they matter
6. **No audio** — animations don't need it, saves ~30% file size

**Transparent mode** (animated WebP):
- Preserves the alpha channel from source videos (e.g. Manim's `-t` flag)
- Uses `libwebp_anim` with `bgra` pixel format for sharp, lossless alpha
- Output works on any background — light, dark, gradient, or patterned
- Embeds as `<img>`, not `<video>` — simpler, auto-animates, no JS needed

## Install

```bash
pip install imageio-ffmpeg
```

Or have `ffmpeg` available on your PATH.

## Usage

```bash
# Single file
python -m airclip video.mp4

# Entire directory
python -m airclip videos/

# Custom settings
python -m airclip video.mp4 --fps 15 --crf 42 --height 480

# Fast mode (skip 2-pass, ~2x faster)
python -m airclip video.mp4 --no-2pass

# Output to a different directory
python -m airclip videos/ --outdir dist/

# Transparent background (outputs animated WebP)
python -m airclip animation.mov --transparent

# Transparent with higher quality
python -m airclip animation.mov --transparent --crf 28
```

### As a library

```python
from airclip import convert_lightweight

result = convert_lightweight(
    "input.mp4",
    output_path="output.webm",
    target_fps=24,
    crf=38,
    max_height=720,
)

# Transparent output (animated WebP)
result = convert_lightweight(
    "animation.mov",
    target_fps=24,
    crf=28,
    transparent=True,
)

print(f"{result['input_kb']:.0f} KB → {result['output_kb']:.0f} KB")
print(f"{result['ratio']:.1f}x smaller")
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--fps` | 24 | Target framerate. Use 15 for near-static content. |
| `--crf` | 38 | Quality level. Higher = smaller. 35-45 works well for animations. |
| `--height` | 720 | Max output height in pixels. |
| `--no-2pass` | off | Skip 2-pass encoding (faster, slightly larger output). |
| `--transparent` | off | Preserve alpha channel. Outputs animated WebP instead of WebM. |
| `--outdir` | same as input | Output directory for converted files. |

## CRF guide

| CRF | Quality | Best for |
|-----|---------|----------|
| 30-34 | High | Live action, complex motion |
| 35-38 | Good | Animations with fine detail |
| 39-42 | Small | Diagrams, slides, code demos |
| 43-50 | Tiny | Static content, simple shapes |

## Embedding on web

### Standard WebM (opaque)

```html
<video autoplay muted loop playsinline>
    <source src="animation.webm" type="video/webm">
</video>
```

```css
video {
    width: 100%;
    background: transparent;
    border: none;
    border-radius: 12px;
}
```

Autoplay on scroll (optional):

```javascript
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        e.isIntersecting ? e.target.play() : e.target.pause();
    });
}, { threshold: 0.5 });

document.querySelectorAll('video').forEach(v => observer.observe(v));
```

### Transparent WebP

```html
<img src="animation.webp" style="width: 100%">
```

No `<video>` element needed — animated WebP auto-plays in all modern browsers and naturally blends into any background.

## Best results when

- Content is vector-like: shapes, text, diagrams, code
- Motion is smooth and predictable (not chaotic)
- No audio needed
- **Standard:** background is a solid or near-solid color
- **Transparent:** source rendered at 720p+ (e.g. `manim -t -qm`) with alpha channel

## Results

### Same animation, three formats

| | Original | Standard Mode | Transparent Mode |
|--|----------|--------------|-----------------|
| **Format** | Manim QTRLE (.mov) | VP9 WebM | Animated WebP |
| **Size** | 2,532 KB | 102 KB | 391 KB |
| **Compression** | — | **24.9x smaller** | **6.5x smaller** |
| **Resolution** | 720p 30fps | 720p 24fps | 720p 24fps |
| **Background** | Alpha channel | Baked in | Alpha preserved |
| **Embed with** | — | `<video>` | `<img>` |

Standard mode bakes the background in — smallest file, works on matching backgrounds.
Transparent mode preserves the alpha channel — larger, but works on any background.

### Across 6 test videos

| Metric | Value |
|--------|-------|
| Average compression | **12x** |
| Total input | ~1.2 MB |
| Total output | ~93 KB |
| Visible quality loss | None |

## License

MIT
