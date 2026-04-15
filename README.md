# airclip

Convert any video to an ultra-lightweight WebM that blends seamlessly into web pages.

**30 seconds of video → ~50-200 KB** without visible quality loss.

## Why

Embedding videos on the web usually means large files, slow loads, and visible player chrome. `airclip` solves this for animation and diagram content:

| Metric | Before | After |
|--------|--------|-------|
| 30s video | ~1-3 MB | ~50-200 KB |
| Format | MP4 (H.264) | WebM (VP9) |
| FPS | 60 | 24 |
| Resolution | 1080p | 720p |
| Audio | Included | Stripped |

The output blends into dark backgrounds — no borders, no player UI, just content that looks native to the page.

## How it works

1. **VP9 encoding** — modern codec designed for web, much better compression than H.264
2. **High CRF** — animation content (solid backgrounds, vector shapes) compresses extremely well at CRF 35-45
3. **Reduced framerate** — 24fps is visually identical to 60fps for slides and diagrams
4. **Downscale to 720p** — on web, nobody notices the difference from 1080p
5. **Two-pass encoding** — analyzes content first, then allocates bits where they matter
6. **No audio** — animations don't need it, saves ~30% file size

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
| `--outdir` | same as input | Output directory for converted files. |

## CRF guide

| CRF | Quality | Best for |
|-----|---------|----------|
| 30-34 | High | Live action, complex motion |
| 35-38 | Good | Animations with fine detail |
| 39-42 | Small | Diagrams, slides, code demos |
| 43-50 | Tiny | Static content, simple shapes |

## Embedding on web

The output is designed to look native on dark-themed pages:

```html
<video autoplay muted loop playsinline>
    <source src="animation.webm" type="video/webm">
    <source src="animation.mp4" type="video/mp4"> <!-- fallback -->
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

For autoplay-on-scroll:

```javascript
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        e.isIntersecting ? e.target.play() : e.target.pause();
    });
}, { threshold: 0.5 });

document.querySelectorAll('video').forEach(v => observer.observe(v));
```

## Best results when

- Background is a solid or near-solid color (dark themes work great)
- Content is vector-like: shapes, text, diagrams, code
- Motion is smooth and predictable (not chaotic)
- No audio needed

## Results

Across 6 test videos: **~1.2 MB → ~93 KB average (12x compression)**. No visible quality loss in browser playback.

## License

MIT
