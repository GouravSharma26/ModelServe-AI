"""Thin CLI wrapper for ModelServe AI reproducible model preparation.

Invokes modelserve.model_preparation.main().
"""

from __future__ import annotations

import sys
from modelserve.model_preparation import main, prepare_model

if __name__ == "__main__":
    main()
