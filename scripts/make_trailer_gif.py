"""
Capture frames from demo_preview.html at key animation timestamps
and combine into assets/trailer.gif using Pillow.

Usage:
    python3 scripts/make_trailer_gif.py
"""
from __future__ import annotations

import io
import pathlib
import sys
from typing import NamedTuple

from PIL import Image

# ---------------------------------------------------------------------------
# Frame schedule: (time_ms, hold_frames)
# time_ms   – animation currentTime to seek to
# hold_frames – how many GIF frames to duplicate (controls pacing)
# ---------------------------------------------------------------------------
class Frame(NamedTuple):
    time_ms: int
    hold: int  # ×80ms per hold unit → display duration in GIF


FRAMES: list[Frame] = [
    # ── Lobby ──────────────────────────────────────────────────────────────
    Frame(400,  3),   # title fades in
    Frame(1000, 4),   # lobby full — logo + classes + button
    Frame(2000, 3),   # hold lobby
    Frame(3500, 3),   # button glow pulse starts
    Frame(4200, 5),   # hover on START RUN
    # ── Boot ───────────────────────────────────────────────────────────────
    Frame(5200, 2),   # boot screen appears
    Frame(5600, 2),   # line 1 fades in
    Frame(6000, 2),   # line 2
    Frame(6300, 2),   # line 3
    Frame(6700, 3),   # line 4 (CONNECTION ESTABLISHED)
    # ── Combat – scenario reveal ──────────────────────────────────────────
    Frame(7200, 2),   # combat screen appears
    Frame(7800, 2),   # log block starts expanding
    Frame(8500, 3),   # scenario text mostly visible
    Frame(9500, 4),   # scenario full + 무역 highlighted
    # ── cat log command ───────────────────────────────────────────────────
    Frame(10200, 2),  # cmd-echo "cat log" visible
    Frame(10800, 3),  # holding
    # ── analyze 무역 typing ───────────────────────────────────────────────
    Frame(12400, 2),  # "a_" typing starts
    Frame(12800, 2),  # "ana_"
    Frame(13200, 2),  # "analyz_"
    Frame(13500, 2),  # "analyze_"
    Frame(13900, 2),  # "analyze 무역_"
    Frame(14200, 2),  # analyze-echo appears
    # ── Success flash ─────────────────────────────────────────────────────
    Frame(14500, 3),  # ✓ CORRECT ANALYSIS flashes in
    Frame(15200, 4),  # success box holds
    Frame(16000, 4),  # TRACE bar updated
    # ── NODE CLEARED badge ────────────────────────────────────────────────
    Frame(15600, 3),  # badge scales in
    Frame(16500, 5),  # badge holds — +10 조각
    Frame(17500, 4),  # badge still visible
    Frame(18200, 2),  # badge fading out
]

DEMO_HTML = pathlib.Path(__file__).parents[1] / "assets" / "demo_preview.html"
OUTPUT_GIF = pathlib.Path(__file__).parents[1] / "assets" / "trailer.gif"
FRAME_DURATION_MS = 80  # base GIF frame duration


def capture_frames() -> list[Image.Image]:
    from playwright.sync_api import sync_playwright

    images: list[Image.Image] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 800, "height": 500})

        # Load local HTML
        page.goto(DEMO_HTML.as_uri())
        page.wait_for_load_state("domcontentloaded")

        # Pause every CSS animation
        page.evaluate(
            "document.getAnimations().forEach(a => { a.pause(); a.currentTime = 0; })"
        )
        # Also freeze JS timers by overriding requestAnimationFrame with no-ops temporarily
        # (we seek manually before each screenshot)

        for frame in FRAMES:
            # Seek all animations to this timestamp
            page.evaluate(
                f"document.getAnimations().forEach(a => {{ a.currentTime = {frame.time_ms}; }})"
            )
            # Give the browser one rAF to paint
            page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

            raw = page.screenshot(type="png")
            img = Image.open(io.BytesIO(raw)).convert("RGBA")

            # Hold this frame by duplicating
            for _ in range(frame.hold):
                images.append(img.copy())

        browser.close()

    return images


def build_gif(images: list[Image.Image]) -> None:
    if not images:
        print("No frames captured!", file=sys.stderr)
        sys.exit(1)

    # Convert to P mode (palette) for smaller GIF
    palettes: list[Image.Image] = []
    for img in images:
        # Convert RGBA → RGB on dark background first, then quantize
        bg = Image.new("RGB", img.size, (10, 14, 20))  # --bg: #0A0E14
        bg.paste(img, mask=img.split()[3])
        quantized = bg.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=1)
        palettes.append(quantized)

    OUTPUT_GIF.parent.mkdir(parents=True, exist_ok=True)
    palettes[0].save(
        OUTPUT_GIF,
        format="GIF",
        save_all=True,
        append_images=palettes[1:],
        optimize=True,
        duration=FRAME_DURATION_MS,
        loop=0,  # infinite loop
    )
    size_kb = OUTPUT_GIF.stat().st_size // 1024
    print(f"✓ Saved {OUTPUT_GIF}  ({len(images)} frames, {size_kb} KB)")


if __name__ == "__main__":
    print("Capturing frames …")
    imgs = capture_frames()
    print(f"  {len(imgs)} frames captured")
    print("Building GIF …")
    build_gif(imgs)
