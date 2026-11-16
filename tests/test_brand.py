"""The brand images follow Home Assistant's rules for icons and logos.

Home Assistant (2026.3 and later) and HACS read them from the integration's own
brand folder. The rules are the ones in Home Assistant's brand image guide: PNG,
transparent, trimmed, icons 256 px square, logos 128 to 256 px on the short side,
and double that for the @2x versions.
"""

from __future__ import annotations

from pathlib import Path
import re

from PIL import Image
import pytest

ROOT = Path(__file__).parent.parent
BRAND = ROOT / "custom_components" / "parcel" / "brand"
SOURCES = ROOT / "brand"

# Every name Home Assistant looks for. A missing dark image falls back to the
# light one, and a missing @2x to the normal size.
KNOWN_NAMES = {
    f"{dark}{kind}{scale}.png"
    for dark in ("", "dark_")
    for kind in ("icon", "logo")
    for scale in ("", "@2x")
}
SHIPPED = ("icon", "logo", "dark_logo")


def load(name: str) -> Image.Image:
    with Image.open(BRAND / name) as image:
        image.load()
        return image


def test_folder_holds_only_what_home_assistant_reads() -> None:
    """HACS needs icon.png; anything Home Assistant doesn't look for is clutter."""
    names = {path.name for path in BRAND.iterdir()}
    assert "icon.png" in names
    assert names <= KNOWN_NAMES, sorted(names - KNOWN_NAMES)
    assert names == {f"{base}{scale}.png" for base in SHIPPED for scale in ("", "@2x")}


def test_icon_is_square_at_both_sizes() -> None:
    assert load("icon.png").size == (256, 256)
    assert load("icon@2x.png").size == (512, 512)


@pytest.mark.parametrize("name", ["logo", "dark_logo"])
def test_logo_is_landscape_and_within_the_size_limits(name: str) -> None:
    width, height = load(f"{name}.png").size
    assert width > height
    assert 128 <= height <= 256
    assert load(f"{name}@2x.png").size == (width * 2, height * 2)


def test_dark_logo_lines_up_with_the_light_one() -> None:
    """Same size and same box; only the lettering changes color."""
    light = load("logo@2x.png")
    dark = load("dark_logo@2x.png")
    assert dark.size == light.size
    box = (0, 0, light.height, light.height)
    assert dark.crop(box).tobytes() == light.crop(box).tobytes()
    assert dark.tobytes() != light.tobytes()


@pytest.mark.parametrize(
    "name", sorted(f"{base}{scale}.png" for base in SHIPPED for scale in ("", "@2x"))
)
def test_image_is_a_transparent_trimmed_png(name: str) -> None:
    image = load(name)
    assert image.format == "PNG"
    assert image.mode == "RGBA"
    alpha = image.getchannel("A")
    assert alpha.getpixel((0, 0)) == 0, "the background must be transparent"
    # Trimmed: the artwork reaches every edge, give or take a hairline that keeps
    # its smoothed outline from being cut off.
    left, top, right, bottom = alpha.getbbox()
    hairline = image.height // 64
    assert left <= hairline
    assert top <= hairline
    assert image.width - right <= hairline
    assert image.height - bottom <= hairline


@pytest.mark.parametrize("source", sorted(path.name for path in SOURCES.glob("*.svg")))
def test_source_draws_without_fonts_or_downloads(source: str) -> None:
    """The build loads no fonts and no files, so the sources can't depend on any."""
    svg = (SOURCES / source).read_text(encoding="utf-8")
    assert not re.search(r"<(text|image|use|style|script|foreignObject)[\s>]", svg)
    links = set(re.findall(r"""["'](https?://[^"']+)["']""", svg))
    assert links == {"http://www.w3.org/2000/svg"}


def test_every_source_is_built() -> None:
    """Each SVG has a line in the build script, and each built image has a source."""
    script = (ROOT / "frontend-src" / "build-brand.mjs").read_text(encoding="utf-8")
    block = script.split("const IMAGES = [", 1)[1].split("];", 1)[0]
    built_from = set(re.findall(r"\['([\w-]+\.svg)'", block))
    assert built_from == {path.name for path in SOURCES.glob("*.svg")}
    outputs = set(re.findall(r"'([\w@-]+\.png)'\)", block))
    assert outputs == {path.name for path in BRAND.iterdir()} | {
        path.name for path in SOURCES.glob("*.png")
    }
