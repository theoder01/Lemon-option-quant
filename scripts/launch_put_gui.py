# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

"""Launch the same GUI from source or the local Windows bundle."""

from pathlib import Path
import sys

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from option_quant.put_gui import main


if __name__ == "__main__":
    main()
