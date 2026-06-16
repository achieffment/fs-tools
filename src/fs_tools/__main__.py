"""`python -m fs_tools` — эквивалент диспетчера `fs-tools`."""
from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
