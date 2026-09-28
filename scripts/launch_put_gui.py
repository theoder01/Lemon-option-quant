# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 28, 2026

"""Launch from any working directory using this checkout's source and database."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from option_quant.put_gui import main


if __name__ == "__main__":
    main(PROJECT_ROOT / "data" / "options.db")
