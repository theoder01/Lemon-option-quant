# Copyright © 2026 Bo Hu. All rights reserved.
"""Create technical derivatives without changing the supplied source artwork."""
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PNG_SIZES = (32, 40, 48, 64, 80, 96, 128, 256)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def main():
    output = ROOT / 'assets' / 'branding'
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(ROOT / 'assets' / 'lemon_option_quant_logo.png') as source:
        if source.width != source.height:
            raise ValueError('Expected the supplied square artwork.')
        artwork = source.convert('RGBA')
        for size in PNG_SIZES:
            artwork.resize((size, size), Image.Resampling.LANCZOS).save(
                output / f'logo-{size}.png'
            )
        # Supply each explicitly resized frame, including the smallest sizes.
        frames = [artwork.resize((s, s), Image.Resampling.LANCZOS) for s in ICO_SIZES]
        frames[-1].save(
            output / 'lemon_option_quant.ico', format='ICO',
            sizes=[(s, s) for s in ICO_SIZES], append_images=frames[:-1],
        )


if __name__ == '__main__':
    main()
