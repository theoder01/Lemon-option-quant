# Lemon Option Quant branding

`lemon_option_quant_logo.png` is the unmodified 980 x 980 artwork supplied by the user.
SHA-256: `3133056B37E8D293950149E507F299A3337CA05BEA7E41FDF2BF3DE6CF38FAAA`.

`branding/` contains technical derivatives only: square PNGs at 32, 40, 48,
64, 80, 96, 128 and 256 pixels, and a Windows ICO with 16, 24, 32, 48, 64,
128 and 256 pixel frames. Colors, background, proportions and artwork are unchanged.

Regenerate with `python scripts/generate_brand_assets.py` after installing
`requirements-build.txt`. The generator uses Pillow LANCZOS resampling and
never overwrites the original. Generated assets are committed source resources,
so routine EXE builds do not need to regenerate them.

The header requests 32 logical pixels using the existing GUI DPI scale and
selects the nearest prepared PNG. Windows uses the multi-resolution ICO through
Tk's normal `iconbitmap(default=...)`; other Tk platforms use `iconphoto`.
PyInstaller embeds the ICO in the EXE and bundles `branding/` for runtime use.
